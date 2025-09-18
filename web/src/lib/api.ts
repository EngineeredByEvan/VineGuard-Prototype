import axios from 'axios';

export interface TelemetryReading {
  id: string;
  device_id: string;
  soil_moisture: number;
  soil_temp_c: number;
  ambient_temp_c: number;
  ambient_humidity: number;
  light_lux: number;
  battery_voltage: number;
  recorded_at: string;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY ?? '';

export async function fetchRecentReadings(): Promise<TelemetryReading[]> {
  const response = await axios.get<TelemetryReading[]>(`${API_BASE_URL}/readings`, {
    headers: {
      'X-API-Key': API_KEY,
    },
    params: {
      limit: 50,
    },
  });
  return response.data;
}

export function openTelemetryStream(onMessage: (reading: TelemetryReading) => void): EventSource | null {
  if (!API_KEY) {
    return null;
  }
  const url = new URL(`${API_BASE_URL}/streams/telemetry`);
  url.searchParams.set('api_key', API_KEY);
  const source = new EventSource(url.toString(), { withCredentials: false });
  source.onmessage = (event) => {
    try {
      const reading = JSON.parse(event.data) as TelemetryReading;
      onMessage(reading);
    } catch (error) {
      console.error('Failed to parse telemetry event', error);
    }
  };
  return source;
}
