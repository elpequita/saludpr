import type { Metadata } from "next";
import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";

export const metadata: Metadata = {
  title: "Acerca · SaludPR",
  description:
    "Por qué existe SaludPR, quién lo construye, y qué principios guían este panel público de salud para Puerto Rico.",
};

export default function AcercaPage() {
  return (
    <main className="relative z-10 min-h-screen">
      <SiteHeader />

      {/* Kicker */}
      <section className="mx-auto max-w-4xl px-6 pt-16 md:pt-24">
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-[var(--color-teal-soft)] rise rise-1">
          Acerca · Un proyecto de Dataurea
        </p>
        <h1 className="mt-5 font-display text-5xl leading-[1.05] tracking-tight text-[var(--color-text)] md:text-6xl rise rise-2">
          Los datos que{" "}
          <span className="italic text-[var(--color-amber-soft)]">
            no aparecían
          </span>{" "}
          en ningún mapa.
        </h1>
        <p className="mt-6 text-lg leading-relaxed text-[var(--color-text-muted)] rise rise-3">
          SaludPR nació de una búsqueda simple que se convirtió en una pregunta
          incómoda: ¿por qué tanta data pública sobre salud en Estados Unidos
          deja a Puerto Rico fuera?
        </p>
      </section>

      {/* Content body */}
      <article className="mx-auto max-w-3xl px-6 py-16">
        <div className="rise rise-4 space-y-14">
          {/* Section 1 — Por qué existe */}
          <section>
            <div className="flex items-center gap-3">
              <div className="h-px w-8 bg-[var(--color-amber)]" />
              <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-[var(--color-text-subtle)]">
                01 · Por qué existe
              </span>
            </div>
            <h2 className="mt-4 font-display text-3xl tracking-tight text-[var(--color-text)]">
              Un hallazgo que me molestó.
            </h2>

            <div className="mt-6 space-y-5 text-[15px] leading-relaxed text-[var(--color-text-muted)]">
              <p>
                Trabajo como analista de datos en salud. Parte de mi rutina es
                revisar indicadores de enfermedades crónicas a nivel condado
                usando fuentes federales — particularmente{" "}
                <a
                  href="https://www.cdc.gov/places/"
                  target="_blank"
                  rel="noreferrer"
                  className="text-[var(--color-amber)] underline-offset-4 hover:underline"
                >
                  CDC PLACES
                </a>
                , el estándar de facto para tasas de diabetes, hipertensión,
                obesidad y otros indicadores de salud a nivel county.
              </p>
              <p>
                Una tarde quise buscar los números para mi propio municipio en
                Puerto Rico. No aparecían. Busqué otros municipios. Tampoco.
                Verifiqué en la documentación oficial de CDC PLACES: los
                estimados cubren los 50 estados y el Distrito de Columbia —
                pero{" "}
                <span className="text-[var(--color-text)]">
                  excluyen a Puerto Rico, Islas Vírgenes, Guam, Samoa Americana
                  y las Marianas del Norte.
                </span>
              </p>
              <p>
                No es un descuido técnico. Es una política explícita. El estándar
                federal para visualizar la salud comunitaria en este país no
                incluye a tres millones de residentes de Puerto Rico. Y no existe
                ningún sustituto público y accesible que lo reemplace.
              </p>
              <p className="text-[var(--color-amber-soft)] italic">
                Construí SaludPR como la herramienta que habría querido encontrar
                esa tarde.
              </p>
            </div>
          </section>

          {/* Section 2 — Qué hace */}
          <section>
            <div className="flex items-center gap-3">
              <div className="h-px w-8 bg-[var(--color-amber)]" />
              <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-[var(--color-text-subtle)]">
                02 · Qué hace
              </span>
            </div>
            <h2 className="mt-4 font-display text-3xl tracking-tight text-[var(--color-text)]">
              Un mapa público, honesto, y bilingüe.
            </h2>

            <div className="mt-6 space-y-5 text-[15px] leading-relaxed text-[var(--color-text-muted)]">
              <p>
                SaludPR reúne datos públicos de US Census, HRSA, CDC, el
                Departamento de Salud de Puerto Rico y CMS, y los presenta en
                un mapa coroplético interactivo.{" "}
                <span className="text-[var(--color-text)]">
                  78 municipios, 939 barrios, 10 indicadores sociales, 5 años
                  de datos.
                </span>
              </p>
              <p>
                Cada valor que ves puede rastrearse hasta su fuente original.
                Cada municipio y barrio tiene coordenadas, población, y una
                bandera que indica si el dato fue observado directamente o
                estimado estadísticamente. No hay inferencias ocultas.
              </p>
              <p>
                El mapa funciona en móvil, está optimizado para conexiones
                lentas, y está disponible gratuitamente para cualquier persona
                — periodistas, investigadores, planificadores municipales,
                o residentes curiosos sobre su propio barrio.
              </p>
            </div>
          </section>

          {/* Section 3 — Quién lo construye */}
          <section>
            <div className="flex items-center gap-3">
              <div className="h-px w-8 bg-[var(--color-amber)]" />
              <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-[var(--color-text-subtle)]">
                03 · Quién lo construye
              </span>
            </div>
            <h2 className="mt-4 font-display text-3xl tracking-tight text-[var(--color-text)]">
              Carlos Pérez.
            </h2>

            <div className="mt-6 space-y-5 text-[15px] leading-relaxed text-[var(--color-text-muted)]">
              <p>
                Soy{" "}
                <span className="text-[var(--color-text)]">
                  analista de datos en salud
                </span>{" "}
                con más de 6 años de experiencia. Tengo una maestría en
                Knowledge Discovery & Data Mining de la Politécnica de Puerto
                Rico (2023) y un bachillerato en Ciencias de Computación de la
                UPR.
              </p>
              <p>
                Nací y me crié en Puerto Rico. Trabajo desde San Juan. Este
                proyecto lo construí en noches y fines de semana porque me
                importa tener herramientas de datos que reflejen fielmente la
                isla donde vivo.
              </p>
              <p>
                SaludPR existe bajo la sombrilla de{" "}
                <a
                  href="https://www.dataurea.com"
                  target="_blank"
                  rel="noreferrer"
                  className="text-[var(--color-amber)] underline-offset-4 hover:underline"
                >
                  Dataurea
                </a>
                , la firma que fundé para ofrecer dashboards, automatización de
                reportes y analítica sanitaria a clínicas, aseguradoras,
                municipios y organizaciones sin fines de lucro en Puerto Rico.
                Si tu organización necesita algo similar a SaludPR pero adaptado
                a tus datos internos —{" "}
                <a
                  href="mailto:carlos.perez@dataurea.com"
                  className="text-[var(--color-text)] underline-offset-4 hover:underline"
                >
                  escríbeme
                </a>
                .
              </p>
            </div>
          </section>

          {/* Section 4 — Principios */}
          <section>
            <div className="flex items-center gap-3">
              <div className="h-px w-8 bg-[var(--color-amber)]" />
              <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-[var(--color-text-subtle)]">
                04 · Principios
              </span>
            </div>
            <h2 className="mt-4 font-display text-3xl tracking-tight text-[var(--color-text)]">
              Lo que no cambia.
            </h2>

            <ul className="mt-6 space-y-4">
              {[
                {
                  title: "Gratuito, para siempre.",
                  body: "SaludPR no tiene — ni tendrá — un paywall, un muro de registro, ni un plan 'premium'. La data pública debe ser pública. Si el proyecto necesita financiamiento, lo buscaremos vía consultoría o becas, no cobrándote a ti.",
                },
                {
                  title: "Código abierto.",
                  body: "Todo el sistema está en GitHub bajo licencia MIT. Cualquier persona puede auditar cómo procesamos la data, replicar la infraestructura en otra jurisdicción, o contribuir mejoras.",
                },
                {
                  title: "Data rastreable.",
                  body: "Cada número incluye una referencia a su fuente original, el año de observación, si fue directamente medido o estimado, y el momento exacto en que lo procesamos. Si SaludPR muestra un dato que no puedes verificar en la fuente, eso es un bug — repórtalo.",
                },
                {
                  title: "Limitaciones explícitas.",
                  body: "Cuando una muestra es muy pequeña para ser confiable, lo decimos. Cuando una fuente federal excluye a Puerto Rico, lo decimos. Cuando un dato tiene supresión estadística, lo mostramos atenuado. La honestidad metodológica no es negociable.",
                },
                {
                  title: "Bilingüe por diseño.",
                  body: "El español es el idioma principal. El inglés existe por accesibilidad internacional, no como opción dominante. Esta jerarquía refleja a quién pertenece el proyecto.",
                },
              ].map((p, i) => (
                <li
                  key={i}
                  className="flex gap-4 border-l-2 border-[var(--color-amber)] pl-5"
                >
                  <div>
                    <h3 className="font-display text-lg text-[var(--color-text)]">
                      {p.title}
                    </h3>
                    <p className="mt-1 text-[14px] leading-relaxed text-[var(--color-text-muted)]">
                      {p.body}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          {/* CTA card */}
          <section className="border border-[var(--color-border)] bg-[var(--color-surface)]/40 p-8">
            <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-[var(--color-teal-soft)]">
              ¿Quieres colaborar?
            </p>
            <div className="mt-3 grid gap-4 md:grid-cols-3">
              <div>
                <h3 className="font-display text-lg text-[var(--color-text)]">
                  Eres periodista
                </h3>
                <p className="mt-1 text-[13px] text-[var(--color-text-muted)]">
                  Cita SaludPR libremente. Si necesitas data customizada para
                  una investigación,{" "}
                  <a
                    href="mailto:carlos.perez@dataurea.com"
                    className="text-[var(--color-amber)] underline-offset-4 hover:underline"
                  >
                    escríbeme
                  </a>
                  .
                </p>
              </div>
              <div>
                <h3 className="font-display text-lg text-[var(--color-text)]">
                  Eres investigador
                </h3>
                <p className="mt-1 text-[13px] text-[var(--color-text-muted)]">
                  La data está bajo CC BY 4.0. Usa la API pública{" "}
                  <Link
                    href="/metodologia"
                    className="text-[var(--color-amber)] underline-offset-4 hover:underline"
                  >
                    documentada aquí
                  </Link>
                  .
                </p>
              </div>
              <div>
                <h3 className="font-display text-lg text-[var(--color-text)]">
                  Eres dev
                </h3>
                <p className="mt-1 text-[13px] text-[var(--color-text-muted)]">
                  Issues, PRs, bugs, ideas bienvenidos en{" "}
                  <a
                    href="https://github.com/elpequita/saludpr"
                    target="_blank"
                    rel="noreferrer"
                    className="text-[var(--color-amber)] underline-offset-4 hover:underline"
                  >
                    GitHub
                  </a>
                  .
                </p>
              </div>
            </div>
          </section>

          {/* Footer nav to map */}
          <div className="flex justify-between border-t border-[var(--color-border)] pt-6">
            <Link
              href="/"
              className="font-mono text-xs uppercase tracking-[0.2em] text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
            >
              ← Volver al mapa
            </Link>
            <Link
              href="/metodologia"
              className="font-mono text-xs uppercase tracking-[0.2em] text-[var(--color-amber)] hover:text-[var(--color-amber-soft)]"
            >
              Leer la metodología →
            </Link>
          </div>
        </div>
      </article>

      <SiteFooter />
    </main>
  );
}
