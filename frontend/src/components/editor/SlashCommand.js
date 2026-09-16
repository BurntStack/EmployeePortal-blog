import { Extension } from '@tiptap/core'
import Suggestion from '@tiptap/suggestion'
import { ReactRenderer } from '@tiptap/react'
import tippy from 'tippy.js'
import SlashCommandMenu from '@/components/editor/SlashCommandMenu.jsx'
import { filterSlashCommands } from '@/components/editor/slashCommandItems.js'

/**
 * Notion-style "/" block picker. Typing "/" opens a filtered command list;
 * picking one deletes the "/query" text and runs that block's command at
 * the cursor. Built on TipTap's own Suggestion utility (the same mechanism
 * behind @mentions), following their documented render pattern.
 */
const SlashCommand = Extension.create({
  name: 'slashCommand',

  addOptions() {
    return {
      suggestion: {
        char: '/',
        command: ({ editor, range, props }) => {
          props.command({ editor, range })
        },
      },
    }
  },

  addProseMirrorPlugins() {
    return [
      Suggestion({
        editor: this.editor,
        ...this.options.suggestion,
        items: ({ query }) => filterSlashCommands(query),
        render: () => {
          let component
          let popup

          return {
            onStart: (props) => {
              component = new ReactRenderer(SlashCommandMenu, {
                props: { items: props.items, command: (item) => props.command(item) },
                editor: props.editor,
              })
              if (!props.clientRect) return
              popup = tippy('body', {
                getReferenceClientRect: props.clientRect,
                appendTo: () => document.body,
                content: component.element,
                showOnCreate: true,
                interactive: true,
                trigger: 'manual',
                placement: 'bottom-start',
              })
            },
            onUpdate(props) {
              component.updateProps({ items: props.items, command: (item) => props.command(item) })
              if (!props.clientRect) return
              popup?.[0]?.setProps({ getReferenceClientRect: props.clientRect })
            },
            onKeyDown(props) {
              if (props.event.key === 'Escape') {
                popup?.[0]?.hide()
                return true
              }
              return component?.ref?.onKeyDown(props) ?? false
            },
            onExit() {
              popup?.[0]?.destroy()
              component?.destroy()
            },
          }
        },
      }),
    ]
  },
})

export default SlashCommand
