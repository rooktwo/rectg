const dateFormat = new Intl.DateTimeFormat('zh-CN', {
  dateStyle: 'medium', timeZone: 'Asia/Ho_Chi_Minh',
});

export function capturedDate(value) {
  const date = value ? new Date(value) : null;
  return date && Number.isFinite(date.getTime()) ? dateFormat.format(date) : null;
}
