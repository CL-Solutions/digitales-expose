// README.md
# Real Estate Investment Exposé

A modern, responsive web application for presenting real estate investment opportunities with a focus on co-living properties.

## Features

- 🏠 Dynamic property exposés
- 💰 Interactive business case calculator
- 📱 Fully responsive design
- 🖨️ Print-optimized layout
- 👨‍💼 Admin interface for content management
- 🚀 Server-side rendering for optimal performance
- 🎨 Corporate design system

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui
- **Database**: PostgreSQL with Prisma ORM
- **State Management**: Zustand
- **Print**: react-to-print

## Getting Started

1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   ```

4. Set up the database:
   ```bash
   npx prisma db push
   ```

5. Run the development server:
   ```bash
   npm run dev
   ```

6. Open [http://localhost:3000](http://localhost:3000)

## Project Structure

```
├── app/
│   ├── expose/[id]/     # Dynamic exposé pages
│   ├── admin/           # Admin interface
│   └── api/             # API routes
├── components/
│   ├── expose/          # Exposé components
│   ├── admin/           # Admin components
│   └── ui/              # shadcn/ui components
├── lib/                 # Utilities and helpers
├── stores/              # Zustand stores
├── types/               # TypeScript types
└── prisma/              # Database schema
```

## Usage

### Viewing an Exposé
Navigate to `/expose/[property-id]` to view a property exposé.

### Admin Interface
Access the admin interface at `/admin` to manage:
- Locations
- Employers
- Images

### Business Case Calculator
Users can adjust parameters like:
- Interest rate
- Repayment rate
- Property appreciation
- Equity capital

## Deployment

The application is optimized for deployment on Vercel or any Node.js hosting platform.

```bash
npm run build
npm start
```

## License