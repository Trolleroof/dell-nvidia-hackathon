"""Live sim driver — single-threaded physics + 60fps MJPEG stream.

The dashboard used to poll ``frames/latest.png`` over HTTP, re-rendering and
re-decoding a 720p PNG every tick while the sim only produced one frame per
``env.step`` (the *settled* pose). The arms appeared to teleport and the feed
ran at ~1.6 fps.

``LiveSimDriver`` fixes both problems:

* It owns the MuJoCo env on one background thread, so it can advance the
  interpolation a few substeps at a time and render *every* intermediate frame.
* It pushes those frames over a single persistent ``multipart/x-mixed-replace``
  (MJPEG) HTTP response, so the browser shows smooth motion with no per-frame
  fetch/decode overhead.

All env mutation (commands, reset) is funnelled through the driver thread via a
queue + lock, so there is exactly one writer of ``MjData`` — no races with the
render call.
"""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from typing import Any, Callable

from factorymind.agent.schemas import CellPlan
from factorymind.sim.a.oracle import oracle_plan
from factorymind.sim.a.render import CellRenderer

# Tuning (all overridable by env so the demo box can be dialled in live).
TARGET_FPS = int(os.environ.get("FACTORYMIND_STREAM_FPS", "60"))
STREAM_HEIGHT = int(os.environ.get("FACTORYMIND_STREAM_HEIGHT", "540"))
STREAM_WIDTH = int(os.environ.get("FACTORYMIND_STREAM_WIDTH", str(STREAM_HEIGHT * 16 // 9)))
JPEG_QUALITY = int(os.environ.get("FACTORYMIND_STREAM_QUALITY", "80"))
# Interpolation substeps consumed per rendered frame. INTERP_STEPS (80) total,
# so 2/frame => a move animates over ~40 frames (~0.7s @ 60fps) — smooth.
SUBSTEPS_PER_FRAME = int(os.environ.get("FACTORYMIND_STREAM_SUBSTEPS", "2"))
IDLE_SUBSTEPS = 1  # keep belt moving / parts settled while no plan is active

OnStepComplete = Callable[[dict[str, Any], CellPlan], None]


class LiveSimDriver:
    def __init__(
        self,
        env_getter: Callable[[], Any],
        on_step_complete: OnStepComplete | None = None,
    ) -> None:
        self._env_getter = env_getter
        self._on_step_complete = on_step_complete

        self._env = env_getter()
        self._renderer: CellRenderer | None = None
        self._renderer_for: Any = None  # model the renderer was built against

        self._lock = threading.RLock()  # guards all env mutation + rendering
        self._plan_queue: deque[CellPlan] = deque()
        self._oracle_steps = 0  # remaining oracle plans to auto-generate
        self._reset_request: tuple | None = None  # (callable,) run on driver thread

        self._active = False  # mid-step (motion in flight)
        self._active_plan: CellPlan | None = None

        # Latest encoded frame + a condition so the stream wakes on each new frame.
        self._frame_cond = threading.Condition()
        self._latest_jpeg: bytes = b""
        self._frame_seq = 0

        self._running = False
        self._thread: threading.Thread | None = None

    # ── lifecycle ──────────────────────────────────────────────────────────────
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="live-sim-driver", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    # ── command surface (called from request handler threads) ───────────────────
    def enqueue_plan(self, plan: CellPlan) -> None:
        """Queue one explicit control plan (e.g. a NemoClaw ``step_cell``)."""
        with self._lock:
            self._plan_queue.append(plan)

    def run_oracle(self, steps: int) -> None:
        """Top up the oracle auto-run counter so the driver keeps animating.

        Capped so the small keep-alive posts the dashboard sends while "playing"
        can't accumulate — Pause then stops motion within a step or two.
        """
        steps = max(0, steps)
        cap = max(steps, 3)
        with self._lock:
            self._oracle_steps = min(self._oracle_steps + steps, cap)

    def request_reset(self, reset_fn: Callable[[], None]) -> None:
        """Run ``reset_fn`` on the driver thread (sole env writer), then clear state."""
        with self._lock:
            self._reset_request = (reset_fn,)

    def is_active(self) -> bool:
        with self._lock:
            return self._active or bool(self._plan_queue) or self._oracle_steps > 0

    @property
    def lock(self) -> threading.RLock:
        """Held by the driver thread per frame; acquire it to mutate the env safely."""
        return self._lock

    def reset_state(self) -> None:
        """Clear queued/active work (call under :attr:`lock` after an external reset)."""
        with self._lock:
            self._plan_queue.clear()
            self._oracle_steps = 0
            self._active = False
            self._active_plan = None

    # ── streaming ──────────────────────────────────────────────────────────────
    def latest_jpeg(self) -> bytes:
        with self._frame_cond:
            return self._latest_jpeg

    def mjpeg_frames(self, boundary: str = "frame"):
        """Generator yielding multipart MJPEG chunks; blocks until each new frame."""
        last_seq = -1
        while self._running:
            with self._frame_cond:
                if self._frame_seq == last_seq:
                    self._frame_cond.wait(timeout=1.0)
                if self._frame_seq == last_seq:
                    continue  # timed out with no new frame — loop and re-check running
                last_seq = self._frame_seq
                jpeg = self._latest_jpeg
            if not jpeg:
                continue
            yield (
                f"--{boundary}\r\n"
                f"Content-Type: image/jpeg\r\n"
                f"Content-Length: {len(jpeg)}\r\n\r\n"
            ).encode() + jpeg + b"\r\n"

    # ── driver thread ──────────────────────────────────────────────────────────
    def _ensure_renderer(self) -> CellRenderer:
        env = self._env_getter()
        model = env.model
        if self._renderer is None or self._renderer_for is not model:
            self._renderer = CellRenderer(model, width=STREAM_WIDTH, height=STREAM_HEIGHT)
            self._renderer_for = model
            self._env = env
        return self._renderer

    def _next_plan(self, env: Any) -> CellPlan | None:
        if self._plan_queue:
            return self._plan_queue.popleft()
        if self._oracle_steps > 0 and not env.get_state().get("done"):
            self._oracle_steps -= 1
            return oracle_plan(env.get_state())
        return None

    def _loop(self) -> None:
        frame_dt = 1.0 / max(1, TARGET_FPS)
        while self._running:
            t0 = time.monotonic()
            try:
                with self._lock:
                    # Handle a pending reset before touching physics.
                    if self._reset_request is not None:
                        (reset_fn,) = self._reset_request
                        self._reset_request = None
                        self._plan_queue.clear()
                        self._oracle_steps = 0
                        self._active = False
                        self._active_plan = None
                        try:
                            reset_fn()
                        except Exception:
                            pass

                    env = self._env_getter()
                    renderer = self._ensure_renderer()

                    if not self._active:
                        plan = self._next_plan(env)
                        if plan is not None:
                            env.apply_plan(plan)
                            self._active = True
                            self._active_plan = plan

                    if self._active:
                        settled = env.advance(SUBSTEPS_PER_FRAME)
                        if settled:
                            state = env.finalize_step()
                            plan = self._active_plan
                            self._active = False
                            self._active_plan = None
                            if self._on_step_complete and plan is not None:
                                try:
                                    self._on_step_complete(state, plan)
                                except Exception:
                                    pass
                    else:
                        env.advance(IDLE_SUBSTEPS)

                    jpeg = renderer.render_jpeg(env.data, quality=JPEG_QUALITY)

                with self._frame_cond:
                    self._latest_jpeg = jpeg
                    self._frame_seq += 1
                    self._frame_cond.notify_all()
            except Exception:
                # Never let a hiccup kill the stream; back off a frame.
                pass

            elapsed = time.monotonic() - t0
            if elapsed < frame_dt:
                time.sleep(frame_dt - elapsed)
