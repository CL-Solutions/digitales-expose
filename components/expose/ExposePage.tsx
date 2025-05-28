// components/expose/ExposePage.tsx (Client Component)
"use client";

import React, { useRef } from 'react';
import { useReactToPrint } from 'react-to-print';
import { Button } from '@/components/ui/button';
import { Printer } from 'lucide-react';
import Header from '@/components/expose/Header';
import LocationOverview from '@/components/expose/LocationOverview';
import InvestmentLocation from '@/components/expose/InvestmentLocation';
import Employers from '@/components/expose/Employers';
import PropertyDetails from '@/components/expose/PropertyDetails';
import MicroLocation from '@/components/expose/MicroLocation';
import Modernization from '@/components/expose/Modernization';
import CoLivingFeatures from '@/components/expose/CoLivingFeatures';
import BusinessCaseCalculator from '@/components/expose/BusinessCaseCalculator';
import Management from '@/components/expose/Management';
import RiskDisclosure from '@/components/expose/RiskDisclosure';
import Footer from '@/components/expose/Footer';

interface ExposePageProps {
  property: any;
  location: any;
}

export default function ExposePage({ property, location }: ExposePageProps) {
  const printRef = useRef<HTMLDivElement>(null);
  
  const handlePrint = useReactToPrint({
    content: () => printRef.current,
    documentTitle: `Expose_${property.address}_${property.unitNumber}`,
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Print/Download Actions - Hidden in print */}
      <div className="fixed top-4 right-4 z-50 flex gap-2 print:hidden">
        <Button
          onClick={handlePrint}
          variant="outline"
          size="sm"
          className="bg-white shadow-lg"
        >
          <Printer className="w-4 h-4 mr-2" />
          Drucken
        </Button>
      </div>

      {/* Main Content */}
      <div ref={printRef} className="bg-white">
        <Header property={property} />
        
        <div className="print:break-after-page">
          <LocationOverview location={location} />
        </div>
        
        <div className="print:break-after-page">
          <InvestmentLocation location={location} />
        </div>
        
        <div className="print:break-after-page">
          <Employers employers={location.employers} />
        </div>
        
        <div className="print:break-after-page">
          <MicroLocation microLocation={property.microLocation} />
        </div>
        
        <PropertyDetails property={property} />
        
        <div className="print:break-after-page">
          <Modernization modernizationDetails={property.modernizationDetails} />
        </div>
        
        <CoLivingFeatures />
        
        <div className="print:break-after-page">
          <BusinessCaseCalculator property={property} />
        </div>
        
        <Management />
        
        <RiskDisclosure />
        
        <Footer />
      </div>
    </div>
  );
}