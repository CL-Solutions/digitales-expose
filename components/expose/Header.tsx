// components/expose/Header.tsx
import React from 'react';
import Image from 'next/image';

interface HeaderProps {
  property: {
    address: string;
    unitNumber: number;
    district: string;
    imageUrl?: string;
  };
}

export default function Header({ property }: HeaderProps) {
  return (
    <div className="relative h-screen w-full overflow-hidden">
      {/* Background Image */}
      <div className="absolute inset-0">
        <Image
          src={property.imageUrl || '/images/nuremberg-hero.jpg'}
          alt={property.address}
          fill
          className="object-cover"
          priority
        />
        <div className="absolute inset-0 bg-gradient-to-r from-black/50 to-transparent" />
      </div>

      {/* Content */}
      <div className="relative z-10 h-full flex items-center">
        <div className="container mx-auto px-6 md:px-12 lg:px-20">
          <div className="max-w-2xl">
            {/* Logo */}
            <div className="mb-8">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-invenio-gold flex items-center justify-center">
                  <span className="text-white font-bold text-xl">III</span>
                </div>
                <div>
                  <h3 className="text-white text-xl font-semibold tracking-wider">INVENIO</h3>
                  <p className="text-white/80 text-xs tracking-widest">REAL ESTATE</p>
                </div>
              </div>
            </div>

            {/* Title */}
            <h1 className="text-white mb-6">
              <span className="block text-5xl md:text-6xl lg:text-7xl font-light mb-4">
                Investment
              </span>
              <span className="block text-5xl md:text-6xl lg:text-7xl font-bold">
                Chance
              </span>
            </h1>

            {/* Property Info */}
            <div className="space-y-2 text-white">
              <h2 className="text-2xl md:text-3xl font-light">
                CO-LIVING NÜRNBERG PRIME
              </h2>
              <p className="text-xl md:text-2xl opacity-90">
                {property.address}
              </p>
              <p className="text-lg opacity-80">
                {property.district}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}