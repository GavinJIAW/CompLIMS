// Exact decimal previews; authoritative calculation remains on the backend.
type Decimal = { value: bigint; scale: number };
function parse(text: unknown): Decimal | null {
  if (!/^\d+(\.\d+)?$/.test(String(text))) return null;
  const [whole, fraction = ''] = String(text).split('.');
  return { value: BigInt(whole + fraction), scale: fraction.length };
}
const power = (n: number) => BigInt(10) ** BigInt(n);
function format(value: Decimal, places?: number): string {
  let { value: number, scale } = value;
  if (places !== undefined) {
    if (scale > places) { const factor = power(scale - places); number = (number + factor / BigInt(2)) / factor; }
    else number *= power(places - scale);
    scale = places;
  }
  const digits = number.toString().padStart(scale + 1, '0');
  return scale ? digits.slice(0, -scale) + '.' + digits.slice(-scale) : digits;
}
export function multiply(left: unknown, right: unknown): string | null {
  const a = parse(left), b = parse(right);
  return a && b ? format({ value: a.value * b.value, scale: a.scale + b.scale }) : null;
}
export function sum(values: (string | null)[], places?: number): string | null {
  const parsed = values.map(parse);
  if (parsed.some(value => value === null)) return null;
  const scale = Math.max(0, ...parsed.map(value => value!.scale));
  const value = parsed.reduce((total, item) => total + item!.value * power(scale - item!.scale), BigInt(0));
  return format({ value, scale }, places);
}
