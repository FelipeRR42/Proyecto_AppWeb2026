import { Armchair, Check, CreditCard, Search } from 'lucide-react'

const steps = [
  {
    number: '01',
    title: 'Encuentra tu viaje',
    description: 'Explora los próximos conciertos y elige tu destino.',
    Icon: Search,
  },
  {
    number: '02',
    title: 'Elige tu asiento',
    description: 'Revisa la disponibilidad y encuentra tu lugar.',
    Icon: Armchair,
  },
  {
    number: '03',
    title: 'Confirma tu reserva',
    description: 'Completa tu compra de forma sencilla y segura.',
    Icon: CreditCard,
  },
  {
    number: '04',
    title: 'Disfruta el concierto',
    description: 'Nosotros nos ocupamos del viaje. Tú, de la música.',
    Icon: Check,
  },
]

export default function HowItWorks() {
  return (
    <section className="how-section" id="como-funciona">
      <div className="how-heading">
        <p className="section-kicker">Así de fácil</p>
        <h2>La música está más cerca</h2>
        <p className="section-description">
          Cuatro pasos sencillos para que solo te preocupes de cantar.
        </p>
      </div>
      <div className="steps-grid">
        {steps.map(({ number, title, description, Icon }) => (
          <article className="step-card" key={number}>
            <div className="step-icon"><Icon size={21} aria-hidden="true" /></div>
            <span className="step-number">{number}</span>
            <h3>{title}</h3>
            <p>{description}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
