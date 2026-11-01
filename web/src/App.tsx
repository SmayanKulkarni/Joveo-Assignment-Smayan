import { Composer } from "./composer/Composer"
import { go, runIdOf, usePath } from "./router"
import { RunPage } from "./run/RunPage"

export function App() {
  const id = runIdOf(usePath())
  return (
    <div className="shell">
      <header>
        <a href="/" onClick={go}>Talent Scout</a>
      </header>
      <main className="column">{id ? <RunPage id={id} key={id} /> : <Composer />}</main>
    </div>
  )
}
