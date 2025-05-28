// types/business-case.ts
export interface BusinessCase {
  purchasePrice: number;
  purchaseCosts: number;
  interestRate: number;
  equityCapital: number;
  repaymentRate: number;
  appreciationRate: number;
  specialDepreciation: number;
  taxRefund: number;
  monthlyRent: number;
  monthlyReserves: number;
  monthlyManagement: number;
}

export interface BusinessCaseResult {
  monthlyIncome: number;
  monthlyExpenses: number;
  monthlySurplus: number;
  propertyValue10Years: number;
  equityBuildup10Years: number;
  remainingDebt10Years: number;
  leverageFactor: number;
}