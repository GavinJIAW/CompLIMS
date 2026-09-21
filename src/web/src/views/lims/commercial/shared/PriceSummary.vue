<template>
  <el-descriptions :column="3" border>
    <el-descriptions-item label="小计 / 人民币含税元">{{
      previewSubtotal ?? form.subtotal ?? '—'
    }}</el-descriptions-item>
    <el-descriptions-item label="调整 / 元">{{ form.adjustment_amount ?? '0.00' }}</el-descriptions-item>
    <el-descriptions-item label="总额 / 人民币含税元">{{
      previewTotal ?? form.total_amount ?? '—'
    }}</el-descriptions-item>
  </el-descriptions>
</template>
<script setup lang="ts">
import { computed } from 'vue';
import { multiply, sum } from '../../shared/decimal';
const props = defineProps<{ form: any }>();
const previewSubtotal = computed(() => {
  if (!Array.isArray(props.form.schemes) || props.form.schemes.some((g: any) => g.source_scheme && !g.id)) return null;
  const rows = props.form.schemes.flatMap((g: any) => g.items || []);
  if (rows.some((row: any) => row.quantity === undefined || row.unit_price === undefined)) return null;
  return sum(
    rows.map((row: any) => sum([multiply(row.quantity, row.unit_price)], 2)),
    2
  );
});
const previewTotal = computed(() => {
  const subtotal = previewSubtotal.value;
  const adjustment = String(props.form.adjustment_amount ?? '0');
  if (subtotal === null || !/^-?\d+(\.\d{1,2})?$/.test(adjustment)) return null;
  const cents = (text: string) => {
    const sign = text.startsWith('-') ? -1n : 1n;
    const [whole, fraction = ''] = text.replace('-', '').split('.');
    return sign * (BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0')));
  };
  const value = cents(subtotal) + cents(adjustment),
    digits = (value < 0n ? -value : value).toString().padStart(3, '0');
  return `${value < 0n ? '-' : ''}${digits.slice(0, -2)}.${digits.slice(-2)}`;
});
</script>
