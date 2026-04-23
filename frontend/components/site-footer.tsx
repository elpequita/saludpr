import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="mt-12 border-t border-[var(--color-border)] bg-[var(--color-ink-soft)]/50">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-6 py-10 text-sm text-[var(--color-text-muted)] md:flex-row md:items-start md:justify-between">
        <div className="flex flex-col gap-3">
          <div className="font-display text-lg text-[var(--color-text)]">
            Salud<span className="text-[var(--color-amber)]">PR</span>
          </div>
          <p className="max-w-sm">
            Panel público y gratuito de datos de salud para Puerto Rico. Un
            proyecto de{" "}
            <a
              href="https://www.dataurea.com"
              target="_blank"
              rel="noreferrer"
              className="text-[var(--color-amber)] underline-offset-4 hover:underline"
            >
              Dataurea
            </a>
            .
          </p>
        </div>

        <div className="flex flex-col gap-2 md:text-right">
          <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-subtle)]">
            Navegación
          </div>
          <Link href="/" className="hover:text-[var(--color-text)]">
            Mapa
          </Link>
          <Link href="/acerca" className="hover:text-[var(--color-text)]">
            Acerca
          </Link>
          <Link
            href="/metodologia"
            className="hover:text-[var(--color-text)]"
          >
            Metodología
          </Link>
          <a
            href="https://github.com/elpequita/saludpr"
            target="_blank"
            rel="noreferrer"
            className="hover:text-[var(--color-text)]"
          >
            Código en GitHub ↗
          </a>
        </div>

        <div className="flex flex-col gap-2 md:text-right">
          <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-subtle)]">
            Licencias
          </div>
          <a
            href="https://creativecommons.org/licenses/by/4.0/"
            target="_blank"
            rel="noreferrer"
            className="hover:text-[var(--color-text)]"
          >
            Datos · CC BY 4.0 ↗
          </a>
          <a
            href="https://opensource.org/licenses/MIT"
            target="_blank"
            rel="noreferrer"
            className="hover:text-[var(--color-text)]"
          >
            Código · MIT ↗
          </a>
        </div>
      </div>

      <div className="border-t border-[var(--color-border)]/50">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4 font-mono text-[10px] uppercase tracking-widest text-[var(--color-text-subtle)]">
          <span>Puerto Rico · 2026</span>
          <span>v0.2</span>
        </div>
      </div>
    </footer>
  );
}
