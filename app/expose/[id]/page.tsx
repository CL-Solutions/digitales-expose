// app/expose/[id]/page.tsx (Server Component - NO "use client")
import { notFound } from 'next/navigation';
import ExposePage from '@/components/expose/ExposePage';

interface PageProps {
  params: { id: string };
}

async function getPropertyData(id: string) {
  try {
    // Mock data for now - replace with actual API calls
    const property = {
      id,
      unitNumber: 48,
      district: 'Schoppershof',
      rooms: 4,
      buildingYear: 1970,
      lastModernization: 2025,
      size: 72,
      floor: '1. OG rechts',
      totalUnits: 11,
      totalFloors: 'EG + 4 OG´s',
      hasBasement: true,
      hasBalcony: true,
      heatingType: 'Gaszentralheizung',
      energyCarrier: '2024',
      energyConsumption: 'neuer Energieausweis wird im Laufe des Jahres erstellt',
      hasElevator: true,
      depreciation: 3,
      reserves: 178465,
      monthlyRent: {
        room1: 475,
        room2: 400,
        room3: 335,
        room4: 375,
      },
      purchasePrice: 379500,
      purchaseCosts: 18183,
      address: 'Hintermayrstr. 3a',
      city: 'Nürnberg',
      imageUrl: '/images/property-hero.jpg',
      modernizationDetails: [
        'Entrümpeln der Wohnung',
        'Entkernung und Abbrucharbeiten der bestehenden Wohnung',
        'Kernsanierung Badezimmer (neues WC, neues Waschbecken)',
        'Erneuerung der Wohnungstüren und Zargen (exkl. Eingangstüre)',
        'Neuer Laminatboden in den Wohnräumen',
        'Erneuern der Fußleisten',
        'Neue Fließen in Betonoptik in den Bädern und sowie Eingangsbereich und Küchenbereich',
        'Verändern des Grundrisses hin zu einer 4-Zimmer Wohnung',
        'Wände und Decken neu verputzen, spachteln und weiß streichen',
        'Einbau einer Maßküche inkl. Elektrogeräte',
        'Streichen der kompletten Wohnung',
      ],
      microLocation: {
        leisure: [
          'Stadtpark Nürnberg',
          'Nürnberg Athletics',
          'Blu Bowl Bowling',
          'TeamEscape Nürnberg',
        ],
        shopping: [
          'Rewe, Edeka, Netto, Lidl, Aldi',
          'Einkaufszentrum Mercado Nürnberg',
          'Shops für den alltäglichen und nicht alltäglichen Gebrauch',
        ],
        infrastructure: {
          uBahn: 'ca. 4 Minuten fußläufig zur nächsten U-Bahn-Haltestelle "Schoppershof"',
          bus: 'ca. 1 Minute fußläufig zur nächsten Bushaltestelle "Nürnberg Welserstr."',
          cityCenter: 'ca. 12 Minuten zum Zentrum Nürnberg',
        },
      },
    };
    
    const location = {
      city: 'Nürnberg',
      inhabitants: 515543,
      populationGrowth: 5.9,
      description: 'Nürnberg ist eine bedeutende Stadt in Bayern...',
      investmentHighlights: [
        'Messe Nürnberg\nNürnberg ist bekannt für seine bedeutende Messegesellschaft.',
        'Automobilindustrie\nNürnberg ist ein wichtiger Standort für die Automobilindustrie.',
        'Medizintechnik\nDie Stadt beheimatet zahlreiche Unternehmen der Medizintechnik-Branche.',
        'Tourismus\nDer Tourismussektor spielt in Nürnberg eine bedeutende Rolle.',
        'Forschung und Entwicklung\nNürnberg ist ein wichtiger Standort für Forschung und Entwicklung.',
        'Mittelstand\nNürnberg ist von einer starken mittelständischen Wirtschaft geprägt.',
      ],
      employers: [
        {
          id: '1',
          name: 'Stadt Nürnberg',
          description: 'Mit gut 11.000 Angestellten ist die Stadt selbst Nürnbergs größter Arbeitgeber.',
          employees: 11000,
        },
        {
          id: '2',
          name: 'SIEMENS AG',
          description: 'Siemens AG ist ein weltweit führendes Technologieunternehmen.',
          employees: 38000,
        },
        {
          id: '3',
          name: 'MAN Truck & Bus',
          description: 'MAN Truck & Bus SE ist ein führendes Unternehmen im Bereich Nutzfahrzeuge.',
          employees: 4000,
        },
        {
          id: '4',
          name: 'DATEV',
          description: 'Die DATEV eG ist ein führendes deutsches Software- und Dienstleistungsunternehmen.',
          employees: 8400,
        },
      ],
      images: [
        { url: '/images/nuremberg-hero.jpg', alt: 'Nürnberg Panorama', category: 'hero' },
        { url: '/images/nuremberg-city.jpg', alt: 'Nürnberg Stadtansicht', category: 'city' },
      ],
    };
    
    return { property, location };
  } catch (error) {
    console.error('Error fetching data:', error);
    return null;
  }
}

export default async function Page({ params }: PageProps) {
  const data = await getPropertyData(params.id);
  
  if (!data) {
    notFound();
  }
  
  return <ExposePage property={data.property} location={data.location} />;
}