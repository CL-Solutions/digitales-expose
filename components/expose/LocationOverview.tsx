// components/expose/LocationOverview.tsx
import React from 'react';
import Image from 'next/image';
import { Users, TrendingUp } from 'lucide-react';

interface LocationOverviewProps {
  location: {
    city: string;
    inhabitants: number;
    populationGrowth: number;
    images: Array<{ url: string; alt: string; category: string }>;
  };
}

export default function LocationOverview({ location }: LocationOverviewProps) {
  const heroImage = location.images.find(img => img.category === 'hero') || location.images[0];
  
  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('de-DE').format(num);
  };

  return (
    <div className="relative min-h-screen">
      {/* Background Image */}
      <div className="absolute inset-0">
        <Image
          src={heroImage?.url || '/images/nuremberg-bridge.jpg'}
          alt={heroImage?.alt || location.city}
          fill
          className="object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-black/60 via-black/40 to-transparent" />
      </div>

      {/* Content */}
      <div className="relative z-10 min-h-screen flex items-center">
        <div className="container mx-auto px-6 md:px-12 lg:px-20">
          <div className="max-w-2xl space-y-8">
            {/* Stats */}
            <div className="space-y-6">
              <div className="bg-white/10 backdrop-blur-md rounded-lg p-6 border border-white/20">
                <div className="flex items-center gap-4 text-white">
                  <Users className="w-8 h-8" />
                  <div>
                    <p className="text-sm opacity-80">Einwohner</p>
                    <p className="text-3xl font-bold">{formatNumber(location.inhabitants)}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white/10 backdrop-blur-md rounded-lg p-6 border border-white/20">
                <div className="flex items-center gap-4 text-white">
                  <TrendingUp className="w-8 h-8" />
                  <div>
                    <p className="text-sm opacity-80">Bevölkerungsentwicklung bis 2030</p>
                    <p className="text-3xl font-bold">+{location.populationGrowth}%</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}