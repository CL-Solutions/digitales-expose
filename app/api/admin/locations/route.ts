// app/api/admin/locations/route.ts
import { NextResponse } from 'next/server';
import { prisma } from '@/lib/db';

export async function GET() {
  try {
    const locations = await prisma.location.findMany({
      include: {
        employers: true,
        images: true,
      },
    });

    return NextResponse.json(locations);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch locations' },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { city, inhabitants, populationGrowth, description, investmentHighlights } = body;

    const location = await prisma.location.create({
      data: {
        city,
        inhabitants: parseInt(inhabitants),
        populationGrowth: parseFloat(populationGrowth),
        description,
        investmentHighlights: investmentHighlights.split('\n').filter(Boolean),
      },
    });

    return NextResponse.json(location);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to create location' },
      { status: 500 }
    );
  }
}