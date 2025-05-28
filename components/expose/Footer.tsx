// components/expose/Footer.tsx
import React from 'react';
import { Phone, Mail, MapPin, Globe } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-gray-900 text-white py-16">
      <div className="container mx-auto px-6 md:px-12 lg:px-20">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-2 gap-12">
            {/* Company Info */}
            <div>
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 bg-invenio-gold flex items-center justify-center">
                  <span className="text-white font-bold text-xl">III</span>
                </div>
                <div>
                  <h3 className="text-xl font-semibold tracking-wider">INVENIO</h3>
                  <p className="text-gray-400 text-xs tracking-widest">REAL ESTATE</p>
                </div>
              </div>
              
              <h4 className="text-lg font-semibold mb-4">INVENIO REAL ESTATE GMBH</h4>
              
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <MapPin className="w-5 h-5 text-invenio-gold mt-0.5 flex-shrink-0" />
                  <div>
                    <p>Münchener Str. 2</p>
                    <p>86633 Neuburg an der Donau</p>
                  </div>
                </div>
                
                <div className="flex items-center gap-3">
                  <Phone className="w-5 h-5 text-invenio-gold flex-shrink-0" />
                  <a href="tel:+4984314363921" className="hover:text-invenio-gold transition-colors">
                    +49 (0) 8431 4363921
                  </a>
                </div>
                
                <div className="flex items-center gap-3">
                  <Mail className="w-5 h-5 text-invenio-gold flex-shrink-0" />
                  <a href="mailto:info@invenio-re.de" className="hover:text-invenio-gold transition-colors">
                    info@invenio-re.de
                  </a>
                </div>
                
                <div className="flex items-center gap-3">
                  <Globe className="w-5 h-5 text-invenio-gold flex-shrink-0" />
                  <a href="https://www.invenio-re.de" target="_blank" rel="noopener noreferrer" className="hover:text-invenio-gold transition-colors">
                    www.invenio-re.de
                  </a>
                </div>
              </div>
            </div>

            {/* Background Image */}
            <div className="relative h-64 md:h-auto rounded-lg overflow-hidden">
              <img
                src="/images/nuremberg-skyline.jpg"
                alt="Nürnberg Skyline"
                className="w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-gray-900/80 to-transparent" />
            </div>
          </div>

          {/* Bottom Bar */}
          <div className="mt-12 pt-8 border-t border-gray-800">
            <div className="flex flex-col md:flex-row justify-between items-center gap-4">
              <p className="text-sm text-gray-400">
                © {new Date().getFullYear()} INVENIO Real Estate GmbH. Alle Rechte vorbehalten.
              </p>
              <div className="flex gap-6 text-sm">
                <a href="#" className="text-gray-400 hover:text-white transition-colors">
                  Impressum
                </a>
                <a href="#" className="text-gray-400 hover:text-white transition-colors">
                  Datenschutz
                </a>
                <a href="#" className="text-gray-400 hover:text-white transition-colors">
                  AGB
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}