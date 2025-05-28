// app/page.tsx (Homepage)
import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 flex items-center justify-center">
      <div className="text-center text-white">
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-16 h-16 bg-invenio-gold flex items-center justify-center">
            <span className="text-white font-bold text-2xl">III</span>
          </div>
          <div className="text-left">
            <h1 className="text-3xl font-semibold tracking-wider">INVENIO</h1>
            <p className="text-gray-400 text-sm tracking-widest">REAL ESTATE</p>
          </div>
        </div>
        
        <h2 className="text-4xl font-light mb-4">Digital Investment Exposé</h2>
        <p className="text-xl text-gray-300 mb-8">
          Moderne Präsentation für Ihre Immobilieninvestition
        </p>
        
        <div className="space-y-4">
          <Link href="/expose/48">
            <Button size="lg" className="bg-invenio-gold hover:bg-invenio-goldDark">
              Demo Exposé ansehen
            </Button>
          </Link>
          <Link href="/admin">
            <Button size="lg" variant="outline" className="text-white border-white hover:bg-white hover:text-gray-900">
              Admin-Bereich
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}