"use client";

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold">TechFlow Automation Platform</h1>
          <p className="text-sm text-muted-foreground">
            Intelligent data extraction and approval workflow
          </p>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="text-center py-12">
          <h2 className="text-xl font-semibold mb-4">Dashboard Ready</h2>
          <p className="text-muted-foreground">
            Frontend foundation is configured with TanStack Query, shadcn/ui, and WebSocket support.
          </p>
        </div>
      </main>
    </div>
  );
}
