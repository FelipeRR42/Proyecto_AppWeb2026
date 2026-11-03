import { ArrowDown, ArrowRight } from 'lucide-react'

export default function HeroSection() {
  return (
    <section className="hero-section" id="inicio">
      <p className="hero-kicker">MiTransporte presenta</p>
      <h1>
        Tu viaje al concierto,
        <span> sin complicaciones.</span>
      </h1>
      <p className="hero-description">
        Encuentra tu próximo viaje, asegura tu asiento y disfruta el camino
        hasta la música.
      </p>
      <div className="hero-actions">
        <a className="btn btn-primary" href="#viajes">
          Ver viajes disponibles <ArrowRight size={15} aria-hidden="true" />
        </a>
        <a className="btn btn-secondary" href="#como-funciona">
          Cómo funciona <ArrowDown size={14} aria-hidden="true" />
        </a>
      </div>
    </section>
  )
}
