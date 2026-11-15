import React from "react";
import type { Band } from "../types";

interface ConfidenceGaugeProps {
  score: number;
  band?: Band;
  size?: number;
  showLabel?: boolean;
}

export default function ConfidenceGauge({
  score,
  band = "green",
  size = 140,
  showLabel = true,
}: ConfidenceGaugeProps) {
  // Normalize score between 0 and 1
  const clampedScore = Math.max(0, Math.min(1, score));
  const percentage = Math.round(clampedScore * 100);

  // SVG dimensions & arc calculations
  const strokeWidth = Math.max(8, Math.round(size * 0.08));
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  // Use a 240 degree gauge arc (from -210 deg to 30 deg)
  const arcLength = circumference * 0.75;
  const strokeDashoffset = arcLength - clampedScore * arcLength;

  // Colors based on band / score
  const colors = {
    green: {
      stroke: "#3E7B54",
      bg: "#EDF5F0",
      text: "#29573B",
      track: "#DFECE3",
      label: "High Certainty",
    },
    yellow: {
      stroke: "#C67D26",
      bg: "#FDF5EB",
      text: "#8A5010",
      track: "#F6E8D6",
      label: "Moderate / Escalate",
    },
    red: {
      stroke: "#BD4C3D",
      bg: "#FDF1EF",
      text: "#863327",
      track: "#F8DDD9",
      label: "Low / Review Req",
    },
  }[band];

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative flex items-center justify-center" style={{ width: size, height: size * 0.85 }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="-rotate-90 transform"
        >
          {/* Background Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={colors.track}
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeLinecap="round"
          />
          {/* Active Fill */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={colors.stroke}
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-700 ease-out"
          />
        </svg>

        {/* Center Readout */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pt-2">
          <span className="font-mono text-2xl font-bold tracking-tight" style={{ color: colors.text }}>
            {percentage}%
          </span>
          <span className="text-[10px] font-mono uppercase tracking-wider text-[#777267]">
            score {clampedScore.toFixed(2)}
          </span>
        </div>
      </div>

      {showLabel && (
        <div className="mt-1 flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium" style={{ background: colors.bg, color: colors.text }}>
          <span className="w-1.5 h-1.5 rounded-full" style={{ background: colors.stroke }} />
          <span>{colors.label}</span>
        </div>
      )}
    </div>
  );
}
