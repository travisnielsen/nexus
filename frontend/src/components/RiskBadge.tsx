import { Flight, getRiskColor, getRiskLabel } from '@/lib/logisticsTypes';

interface RiskBadgeProps {
  riskLevel: Flight['riskLevel'];
  showLabel?: boolean;
  size?: 'sm' | 'md';
}

export function RiskBadge({ riskLevel, showLabel = true, size = 'md' }: RiskBadgeProps) {
  const color = getRiskColor(riskLevel);
  const label = getRiskLabel(riskLevel);
  
  const sizeClasses = size === 'sm' 
    ? 'px-2 py-0.5 text-xs' 
    : 'px-3 py-1 text-sm';

  return (
    <span
      style={{ backgroundColor: `${color}20`, color: color, borderColor: color }}
      className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${sizeClasses}`}
    >
      <span 
        className={`rounded-full ${size === 'sm' ? 'w-1.5 h-1.5' : 'w-2 h-2'}`}
        style={{ backgroundColor: color }}
      />
      {showLabel && label}
    </span>
  );
}
