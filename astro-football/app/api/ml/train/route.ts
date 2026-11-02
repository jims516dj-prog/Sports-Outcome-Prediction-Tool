import { handle } from "@/lib/api";
import { retrain } from "@/lib/ml/combination_discoverer";

export async function POST() {
  return handle(() => retrain());
}
