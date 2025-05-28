// app/api/properties/[id]/route.ts
import { NextResponse } from 'next/server';

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    // This would normally fetch from your external API
    // For now, returning mock data
    const propertyData = {
      id: params.id,
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
      postalCode: '90409',
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

    return NextResponse.json(propertyData);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch property data' },
      { status: 500 }
    );
  }
}