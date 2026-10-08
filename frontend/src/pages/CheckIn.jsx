// Flujo 2 (Vittorio): el staff ingresa evento + PIN y escanea el QR con la cámara
// (sugerencia: librería html5-qrcode). Llama a api.checkin y muestra verde/rojo.
export default function CheckIn() {
  return (
    <section className="angosto">
      <h1>Check-in</h1>
      <p className="muted">
        Para el staff en la puerta: escanea el código QR del boleto para registrar la entrada.
      </p>
      <p className="alerta">En construcción (Flujo 2).</p>
    </section>
  )
}
