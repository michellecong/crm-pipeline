# CRM Pipeline Frontend

React + TypeScript frontend application for four-stage content generation pipeline.

## Features

- 📝 Enter company name to automatically generate content
- 🎯 Four-stage generation pipeline:
  1. **Product Catalog** (Products) - Generate product list from web content
  2. **Buyer Personas** (Personas) - Generate target customer personas based on products and content
  3. **Pain-Point Mappings** (Mappings) - Generate pain-point to value proposition mappings for each persona
  4. **Outreach Sequences** (Sequences) - Generate sales outreach sequences
- 📊 Real-time generation statistics display
- 🎨 Modern responsive UI design

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Axios** - HTTP client

## Installation and Running

### Prerequisites

- Node.js 18+
- npm or yarn

### Install Dependencies

```bash
cd frontend
npm install
```

### Development Mode

```bash
npm run dev
```

The application will start at `http://localhost:3000`.

### Build for Production

```bash
npm run build
```

Build output will be in the `dist` directory.

### Preview Production Build

```bash
npm run preview
```

## Configuration

### API Address

The default API address is `http://localhost:8000`. To modify it:

1. Create a `.env` file:

```env
VITE_API_BASE_URL=http://your-api-url:8000
```

2. Or modify the proxy configuration in `vite.config.ts`.

## Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── ProductsSection.tsx
│   │   ├── PersonasSection.tsx
│   │   ├── MappingsSection.tsx
│   │   ├── SequencesSection.tsx
│   │   ├── StatisticsSection.tsx
│   │   └── Section.css
│   ├── services/            # API services
│   │   └── api.ts
│   ├── types/               # TypeScript type definitions
│   │   └── api.ts
│   ├── App.tsx              # Main application component
│   ├── App.css              # Main stylesheet
│   ├── main.tsx             # Entry point
│   └── index.css             # Global styles
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## Usage

1. **Start Backend Service**

   ```bash
   # In project root directory
   python -m uvicorn app.main:app --reload
   ```

2. **Start Frontend Service**

   ```bash
   cd frontend
   npm run dev
   ```

3. **Use the Application**
   - Enter a company name in the input field (e.g., Salesforce)
   - Select the number of personas to generate (3-12)
   - Click the "Generate" button
   - Wait for generation to complete and view the results

## API Endpoints

The frontend calls the following backend API:

- `POST /api/v1/llm/pipeline/generate` - Execute four-stage generation pipeline

## Browser Support

- Chrome (latest version)
- Firefox (latest version)
- Safari (latest version)
- Edge (latest version)

## Development

### Code Standards

The project uses ESLint for code checking:

```bash
npm run lint
```

### Type Checking

TypeScript is configured in strict mode to ensure type safety.

## License

Same as the main project.
