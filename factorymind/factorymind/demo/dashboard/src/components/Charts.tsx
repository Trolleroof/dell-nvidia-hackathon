import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartPoint } from "../hooks/useTelemetry";
import { COLORS } from "../theme";

const axis = { stroke: COLORS.faint, fontSize: 11 };
const tooltipStyle = {
  background: "#0c0f14",
  border: `1px solid ${COLORS.line}`,
  borderRadius: 10,
  fontSize: 12,
};

export function ThroughputChart({ data }: { data: ChartPoint[] }) {
  return (
    <div className="card">
      <h2 className="card-title"><span className="tick" />Throughput Over Time · tokens/sec</h2>
      <ResponsiveContainer width="100%" height={230}>
        <AreaChart data={data} margin={{ top: 8, right: 10, left: -10, bottom: 0 }}>
          <defs>
            <linearGradient id="gD" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={COLORS.nvidiaBright} stopOpacity={0.35} />
              <stop offset="100%" stopColor={COLORS.nvidiaBright} stopOpacity={0} />
            </linearGradient>
            <linearGradient id="gA" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={COLORS.dellBright} stopOpacity={0.3} />
              <stop offset="100%" stopColor={COLORS.dellBright} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={COLORS.line} vertical={false} />
          <XAxis dataKey="step" tick={axis} stroke={COLORS.line} />
          <YAxis tick={axis} stroke={COLORS.line} width={44} />
          <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: COLORS.dim }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Area type="monotone" dataKey="diffusion" name="DiffusionGemma" stroke={COLORS.nvidiaBright} fill="url(#gD)" strokeWidth={2.5} isAnimationActive={false} dot={false} />
          <Area type="monotone" dataKey="ar" name="Gemma 4 (AR)" stroke={COLORS.dellBright} fill="url(#gA)" strokeWidth={2.5} isAnimationActive={false} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function LatencyChart({ data, cloud }: { data: ChartPoint[]; cloud: boolean }) {
  return (
    <div className="card">
      <h2 className="card-title"><span className="tick" />End-to-End Latency Over Time · ms / decision</h2>
      <ResponsiveContainer width="100%" height={230}>
        <LineChart data={data} margin={{ top: 8, right: 10, left: -10, bottom: 0 }}>
          <CartesianGrid stroke={COLORS.line} vertical={false} />
          <XAxis dataKey="step" tick={axis} stroke={COLORS.line} />
          <YAxis tick={axis} stroke={COLORS.line} width={44} />
          <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: COLORS.dim }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line type="monotone" dataKey="diffusion" name="DiffusionGemma" stroke={COLORS.nvidiaBright} strokeWidth={2.5} isAnimationActive={false} dot={false} />
          <Line type="monotone" dataKey="ar" name="Gemma 4 (AR)" stroke={COLORS.dellBright} strokeWidth={2.5} isAnimationActive={false} dot={false} />
          {cloud && (
            <Line type="monotone" dataKey="cloud" name="Cloud (simulated)" stroke={COLORS.cloud} strokeWidth={2.5} strokeDasharray="5 4" isAnimationActive={false} dot={false} />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
