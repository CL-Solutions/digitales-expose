// app/api/locations/[city]/route.ts
import { NextResponse } from 'next/server';
import { prisma } from '@/lib/db';

export async function GET(
  request: Request,
  { params }: { params: { city: string } }
) {
  try {
    const location = await prisma.location.findUnique({
      where: { city: params.city },
      include: {
        employers: true,
        images: true,
      },
    });

    if (!location) {
      return NextResponse.json(
        { error: 'Location not found' },
        { status: 404 }
      );
    }

    return NextResponse.json(location);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch location data' },
      { status: 500 }
    );
  }
}