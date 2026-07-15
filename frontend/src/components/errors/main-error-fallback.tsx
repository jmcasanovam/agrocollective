"use client";

export function MainErrorFallback({ error }: { error: Error }) {
  return (
    <div className="flex h-screen overflow-y-auto flex-col items-center justify-center gap-4 p-8 text-center">
      <h1 className="text-2xl font-bold text-red-600">Algo ha salido mal</h1>
      <p className="text-gray-600">{error.message}</p>
      <button
        onClick={() => window.location.reload()}
        className="rounded bg-green-700 px-4 py-2 text-white hover:bg-green-800"
      >
        Recargar página
      </button>
    </div>
  );
}
