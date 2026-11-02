import { useState } from "react"
import type { KeyboardEvent } from "react"
import { Plus, X } from "lucide-react"

type Props = { label: string; items: string[]; max: number; maxChars: number; added?: Set<string>; onChange: (items: string[]) => void }

// A list you add to and remove from. `added` marks items the server says the CSM put there.
export function ChipList({ label, items, max, maxChars, added, onChange }: Props) {
  const [value, setValue] = useState("")

  function add() {
    const item = value.trim()
    if (item && !items.includes(item)) onChange([...items, item])
    setValue("")
  }

  // Enter adds the item and must not submit anything around this list.
  function onKeyDown(event: KeyboardEvent) {
    if (event.key !== "Enter") return
    event.preventDefault()
    add()
  }

  return (
    <div className="chips-edit">
      <ul>
        {items.map((item) => (
          <li key={item} className={added?.has(item) ? "tag added" : "tag"}>
            {item}
            {added?.has(item) && <span className="sr-only"> (added by CSM)</span>}
            <button type="button" aria-label={`Remove ${item}`} onClick={() => onChange(items.filter((i) => i !== item))}>
              <X size={13} aria-hidden />
            </button>
          </li>
        ))}
      </ul>
      <span className="chip-add">
        <input className="field" placeholder={`Add a ${label}`} value={value} maxLength={maxChars} onChange={(e) => setValue(e.target.value)} onKeyDown={onKeyDown} aria-label={`Add ${label}`} disabled={items.length >= max} />
        <button type="button" onClick={add} disabled={items.length >= max || !value.trim()}>
          <Plus size={16} aria-hidden /> Add
        </button>
      </span>
    </div>
  )
}
