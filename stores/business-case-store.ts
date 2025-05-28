// stores/business-case-store.ts
import { create } from 'zustand';
import { BusinessCase } from '@/types/business-case';

interface BusinessCaseStore {
  businessCase: BusinessCase;
  updateBusinessCase: (updates: Partial<BusinessCase>) => void;
  resetBusinessCase: (initial: BusinessCase) => void;
}

export const useBusinessCaseStore = create<BusinessCaseStore>((set) => ({
  businessCase: {
    purchasePrice: 0,
    purchaseCosts: 0,
    interestRate: 4.3,
    equityCapital: 0,
    repaymentRate: 1.2,
    appreciationRate: 2,
    specialDepreciation: 29000,
    taxRefund: 12180,
    monthlyRent: 0,
    monthlyReserves: 62,
    monthlyManagement: 167,
  },
  updateBusinessCase: (updates) =>
    set((state) => ({
      businessCase: { ...state.businessCase, ...updates },
    })),
  resetBusinessCase: (initial) =>
    set({ businessCase: initial }),
}));