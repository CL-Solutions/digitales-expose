// lib/calculations.ts
import { BusinessCase, BusinessCaseResult } from '@/types/business-case';

export function calculateBusinessCase(params: BusinessCase): BusinessCaseResult {
  const loanAmount = params.purchasePrice + params.purchaseCosts - params.equityCapital;
  const monthlyInterest = (loanAmount * params.interestRate) / 100 / 12;
  const monthlyRepayment = (loanAmount * params.repaymentRate) / 100 / 12;
  const monthlyFinancing = monthlyInterest + monthlyRepayment;
  
  const monthlyIncome = params.monthlyRent;
  const monthlyExpenses = monthlyFinancing + params.monthlyReserves + params.monthlyManagement;
  const monthlySurplus = monthlyIncome - monthlyExpenses;
  
  // 10-year calculations
  const propertyValue10Years = params.purchasePrice * Math.pow(1 + params.appreciationRate / 100, 10);
  const totalRepayment10Years = monthlyRepayment * 12 * 10;
  const remainingDebt10Years = loanAmount - totalRepayment10Years;
  const equityBuildup10Years = propertyValue10Years - remainingDebt10Years;
  
  // Leverage factor
  const totalInvested = params.equityCapital - params.specialDepreciation - params.taxRefund + (monthlySurplus < 0 ? Math.abs(monthlySurplus) * 12 * 10 : 0);
  const leverageFactor = equityBuildup10Years / totalInvested;
  
  return {
    monthlyIncome,
    monthlyExpenses,
    monthlySurplus,
    propertyValue10Years,
    equityBuildup10Years,
    remainingDebt10Years,
    leverageFactor,
  };
}