import { useEffect, useState } from 'react'
import { LineChart, Line, Tooltip, ResponsiveContainer } from 'recharts'
import { useApiClient } from '../api/client'

interface SparklinePoint {
  date: string
  belegungsgrad_pct: number
}

interface Props {
  locationId: string
}

export default function BelegungSparkline({ locationId }: Props) {
  const { get } = useApiClient()
  const [data, setData] = useState<SparklinePoint[]>([])

  useEffect(() => {
    const today = new Date()
    const dateTo = today.toISOString().slice(0, 10)
    const dateFrom = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
    get<{ data: SparklinePoint[] }>(
      `/api/statistics/occupancy?location_id=${locationId}&date_from=${dateFrom}&date_to=${dateTo}&granularity=day`
    )
      .then((res) => setData(res.data))
      .catch(() => {})
  }, [locationId, get])

  if (data.length === 0) return null

  return (
    <ResponsiveContainer width={200} height={50}>
      <LineChart data={data}>
        <Line
          type="monotone"
          dataKey="belegungsgrad_pct"
          stroke="#a5d6a7"
          dot={false}
          strokeWidth={2}
        />
        <Tooltip
          formatter={(v: number) => [`${v} %`, 'Auslastung']}
          labelFormatter={(l: string) => l}
          contentStyle={{ fontSize: 11 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
