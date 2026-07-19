export function invoiceTotal(lines) {
  const total = lines.reduce((sum, line) => {
    const taxed = line.unitPrice * line.quantity * (1 + line.taxRate);
    return sum + Math.round(taxed * 100) / 100;
  }, 0);
  return Math.round(total * 100) / 100;
}
