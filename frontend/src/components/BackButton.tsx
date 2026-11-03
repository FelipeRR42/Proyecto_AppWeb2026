import { ArrowLeft } from 'lucide-react'
import type { MouseEvent } from 'react'

export default function BackButton() {
  function handleClick(event: MouseEvent<HTMLAnchorElement>) {
    if (!document.referrer) return

    const previousUrl = new URL(document.referrer)
    if (previousUrl.origin !== window.location.origin) return

    event.preventDefault()
    window.history.back()
  }

  return (
    <a
      className="back-button account-button"
      href="/"
      onClick={handleClick}
      aria-label="Volver a la página anterior"
    >
      <ArrowLeft size={14} aria-hidden="true" />
      <span>Volver</span>
    </a>
  )
}
