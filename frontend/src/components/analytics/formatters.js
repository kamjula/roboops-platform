export function formatTimestamp(value, showDate = false) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  const time = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return showDate ? `${date.toLocaleDateString()} ${time}` : time;
}

export function formatSensorValue(value, unit) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "Unavailable";
  const number = Number(value);
  const decimals = Math.abs(number) < 1 ? 3 : Math.abs(number) >= 100 ? 1 : 2;
  return `${number.toFixed(decimals)} ${unit ?? ""}`.trim();
}
