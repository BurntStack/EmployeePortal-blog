import { forwardRef, useEffect, useImperativeHandle, useState } from 'react'
import { cn } from '@/utils/cn.js'

/**
 * The floating list rendered by the "/" suggestion. TipTap drives this
 * imperatively (it's mounted via ReactRenderer, not normal React tree), so
 * keyboard handling is exposed through the ref per TipTap's own documented
 * pattern for suggestion UIs.
 */
const SlashCommandMenu = forwardRef(function SlashCommandMenu({ items, command }, ref) {
  const [selected, setSelected] = useState(0)

  useEffect(() => setSelected(0), [items])

  const select = (index) => {
    const item = items[index]
    if (item) command(item)
  }

  useImperativeHandle(ref, () => ({
    onKeyDown({ event }) {
      if (event.key === 'ArrowUp') {
        setSelected((i) => (i + items.length - 1) % items.length)
        return true
      }
      if (event.key === 'ArrowDown') {
        setSelected((i) => (i + 1) % items.length)
        return true
      }
      if (event.key === 'Enter') {
        select(selected)
        return true
      }
      return false
    },
  }))

  if (items.length === 0) {
    return (
      <div className="w-56 rounded-xl border border-line-strong bg-white p-2 text-sm text-mute shadow-lg">
        No matches
      </div>
    )
  }

  return (
    <div className="max-h-72 w-56 overflow-y-auto rounded-xl border border-line-strong bg-white p-1.5 shadow-lg">
      {items.map((item, index) => (
        <button
          key={item.title}
          type="button"
          onClick={() => select(index)}
          onMouseEnter={() => setSelected(index)}
          className={cn(
            'flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition-colors',
            index === selected ? 'bg-orange-500/10 text-orange-700' : 'text-ink hover:bg-sand',
          )}
        >
          <item.icon className="h-4 w-4 shrink-0" />
          {item.title}
        </button>
      ))}
    </div>
  )
})

export default SlashCommandMenu
