import type { PartName, SensorName } from './api'

// Sound is a stretch Sensor the backend doesn't score yet, so pages leave it out.
export const SENSORS: { name: SensorName; label: string; unit: string; part: PartName }[] = [
  { name: 'heart_rate', label: 'Heart rate', unit: 'bpm', part: 'heart_rate' },
  { name: 'temperature', label: 'Temperature', unit: '°C', part: 'environment' },
  { name: 'humidity', label: 'Humidity', unit: '%', part: 'environment' },
  { name: 'motion', label: 'Motion', unit: '/30 s', part: 'restlessness' },
]

export const PART_NAMES: PartName[] = ['duration', 'restlessness', 'heart_rate', 'environment']
export const PART_LABELS: Record<PartName, string> = {
  duration: 'Duration',
  restlessness: 'Restlessness',
  heart_rate: 'Heart rate',
  environment: 'Environment',
}

// The API speaks UTC; the Sleeper reads local time.
export const clock = (iso: string | number) =>
  new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
export const day = (iso: string) => new Date(iso).toLocaleDateString([], { weekday: 'short', day: 'numeric', month: 'short' })
export const duration = (ms: number) => {
  const m = Math.round(ms / 60_000)
  return `${Math.floor(m / 60)} h ${m % 60} min`
}
export const between = (from: string, to: string) => duration(Date.parse(to) - Date.parse(from))
