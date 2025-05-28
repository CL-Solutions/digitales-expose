// components/expose/BusinessCaseCalculator.tsx
"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Euro, TrendingUp, Building, Calculator } from 'lucide-react';
import { useBusinessCaseStore } from '@/stores/business-case-store';
import { calculateBusinessCase } from '@/lib/calculations';

interface BusinessCaseCalculatorProps {
  property: {
    purchasePrice: number;
    monthlyRent: number;
  };
}

export default function BusinessCaseCalculator({ property }: BusinessCaseCalculatorProps) {
  const { businessCase, updateBusinessCase } = useBusinessCaseStore();
  const [results, setResults] = useState<any>(null);
  const [financingType, setFinancingType] = useState<'100' | '90'>('100');

  // Initialize business case with property data
  useEffect(() => {
    updateBusinessCase({
      purchasePrice: property.purchasePrice,
      monthlyRent: property.monthlyRent,
      purchaseCosts: property.purchasePrice * 0.048, // ~4.8% Nebenkosten
      equityCapital: financingType === '100' ? property.purchasePrice * 0.048 : property.purchasePrice * 0.148,
    });
  }, [property, financingType]);

  // Calculate results whenever business case changes
  useEffect(() => {
    const calculated = calculateBusinessCase(businessCase);
    setResults(calculated);
  }, [businessCase]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('de-DE', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  return (
    <div className="py-16 px-6 md:px-12 lg:px-20 bg-gray-50">
      <div className="container mx-auto max-w-6xl">
        <h2 className="text-4xl font-bold mb-2">Business Case</h2>
        <p className="text-xl text-gray-600 mb-8">Ihre individuelle Investitionsberechnung</p>

        <Tabs value={financingType} onValueChange={(v) => setFinancingType(v as '100' | '90')}>
          <TabsList className="grid w-full max-w-md grid-cols-2 mb-8">
            <TabsTrigger value="100">100% Finanzierung</TabsTrigger>
            <TabsTrigger value="90">90% Finanzierung</TabsTrigger>
          </TabsList>

          <TabsContent value={financingType} className="space-y-8">
            {/* Input Controls */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calculator className="w-5 h-5" />
                  Parameter anpassen
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <Label>Zinssatz: {businessCase.interestRate}%</Label>
                    <Slider
                      value={[businessCase.interestRate]}
                      onValueChange={([value]) => updateBusinessCase({ interestRate: value })}
                      min={2}
                      max={6}
                      step={0.1}
                      className="mt-2"
                    />
                  </div>
                  
                  <div>
                    <Label>Tilgung: {businessCase.repaymentRate}%</Label>
                    <Slider
                      value={[businessCase.repaymentRate]}
                      onValueChange={([value]) => updateBusinessCase({ repaymentRate: value })}
                      min={1}
                      max={4}
                      step={0.1}
                      className="mt-2"
                    />
                  </div>
                  
                  <div>
                    <Label>Wertsteigerung p.a.: {businessCase.appreciationRate}%</Label>
                    <Slider
                      value={[businessCase.appreciationRate]}
                      onValueChange={([value]) => updateBusinessCase({ appreciationRate: value })}
                      min={0}
                      max={5}
                      step={0.5}
                      className="mt-2"
                    />
                  </div>
                  
                  <div>
                    <Label>Eigenkapital: {formatCurrency(businessCase.equityCapital)}</Label>
                    <Slider
                      value={[businessCase.equityCapital]}
                      onValueChange={([value]) => updateBusinessCase({ equityCapital: value })}
                      min={0}
                      max={businessCase.purchasePrice * 0.4}
                      step={1000}
                      className="mt-2"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Results */}
            {results && (
              <>
                {/* Monthly Cash Flow */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Euro className="w-5 h-5" />
                      Monatliche Berechnung
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid md:grid-cols-2 gap-8">
                      <div>
                        <h4 className="font-semibold mb-4 text-green-600">Einnahmen</h4>
                        <div className="space-y-2">
                          <div className="flex justify-between">
                            <span>Miete</span>
                            <span className="font-semibold">{formatCurrency(results.monthlyIncome)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Steuervorteil</span>
                            <span className="font-semibold">{formatCurrency(335.52)}</span>
                          </div>
                          <div className="border-t pt-2 font-bold flex justify-between">
                            <span>Gesamt</span>
                            <span className="text-green-600">{formatCurrency(results.monthlyIncome + 335.52)}</span>
                          </div>
                        </div>
                      </div>
                      
                      <div>
                        <h4 className="font-semibold mb-4 text-red-600">Ausgaben</h4>
                        <div className="space-y-2">
                          <div className="flex justify-between">
                            <span>Finanzierung</span>
                            <span className="font-semibold">{formatCurrency(results.monthlyExpenses - 229)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Rücklagen</span>
                            <span className="font-semibold">{formatCurrency(62)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Verwaltung</span>
                            <span className="font-semibold">{formatCurrency(167)}</span>
                          </div>
                          <div className="border-t pt-2 font-bold flex justify-between">
                            <span>Gesamt</span>
                            <span className="text-red-600">{formatCurrency(results.monthlyExpenses)}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <div className="mt-6 p-4 bg-gray-100 rounded-lg">
                      <div className="flex justify-between items-center">
                        <span className="text-lg font-semibold">Monatlicher Überschuss</span>
                        <span className={`text-2xl font-bold ${results.monthlySurplus >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrency(results.monthlySurplus + 335.52)}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* 10 Year Projection */}
                <Card className="bg-invenio-beige border-invenio-gold">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <TrendingUp className="w-5 h-5" />
                      Vermögensaufbau nach 10 Jahren
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid md:grid-cols-3 gap-6 text-center">
                      <div className="space-y-2">
                        <Building className="w-12 h-12 mx-auto text-invenio-gold" />
                        <p className="text-sm text-gray-600">Immobilienwert</p>
                        <p className="text-2xl font-bold">{formatCurrency(results.propertyValue10Years)}</p>
                      </div>
                      
                      <div className="space-y-2">
                        <div className="w-12 h-12 mx-auto bg-green-100 rounded-full flex items-center justify-center">
                          <span className="text-green-600 font-bold">€</span>
                        </div>
                        <p className="text-sm text-gray-600">Aufgebautes Vermögen</p>
                        <p className="text-2xl font-bold text-green-600">{formatCurrency(results.equityBuildup10Years)}</p>
                      </div>
                      
                      <div className="space-y-2">
                        <div className="w-12 h-12 mx-auto bg-invenio-gold rounded-full flex items-center justify-center">
                          <span className="text-white font-bold">x{results.leverageFactor.toFixed(1)}</span>
                        </div>
                        <p className="text-sm text-gray-600">Hebelfaktor</p>
                        <p className="text-lg">Für jeden eingesetzten Euro</p>
                      </div>
                    </div>
                    
                    <div className="mt-8 p-4 bg-white rounded-lg">
                      <p className="text-sm text-gray-600 mb-2">Restschuld nach 10 Jahren</p>
                      <p className="text-xl font-semibold">{formatCurrency(results.remainingDebt10Years)}</p>
                    </div>
                  </CardContent>
                </Card>

                {/* Special Benefits */}
                <Card>
                  <CardHeader>
                    <CardTitle>Einmalige Vorteile</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid md:grid-cols-2 gap-4">
                      <div className="p-4 bg-green-50 rounded-lg">
                        <p className="text-sm text-gray-600">Sonderabschreibung (einmalig)</p>
                        <p className="text-xl font-bold text-green-600">{formatCurrency(businessCase.specialDepreciation)}</p>
                      </div>
                      <div className="p-4 bg-green-50 rounded-lg">
                        <p className="text-sm text-gray-600">Steuererstattung (einmalig)</p>
                        <p className="text-xl font-bold text-green-600">{formatCurrency(businessCase.taxRefund)}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}