import { useState } from 'react'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Image from '@tiptap/extension-image'
import Placeholder from '@tiptap/extension-placeholder'
import { AnimatePresence, motion } from 'framer-motion'
import Toolbar from '@/components/editor/Toolbar.jsx'
import { uploadContentImage } from '@/lib/uploadImage.js'

function imageFileFrom(fileList) {
  return Array.from(fileList || []).find((f) => f.type.startsWith('image/'))
}

/**
 * Rich text post editor: formatting toolbar, drag-drop / paste / toolbar
 * image upload (embedded as a URL, never inlined as base64), sticky
 * toolbar. `content` seeds the initial document only — the caller (see
 * PostEditor.jsx) gates rendering behind its own `loading` state so this
 * mounts once with the right value already in hand, rather than this
 * component trying to imperatively resync an existing editor instance
 * (which is a known crash under React 19 StrictMode's double-effect
 * invocation — `editor.commands.setContent()` on a not-yet-settled view).
 * `onChange` fires HTML on every edit.
 */
export default function RichTextEditor({ content, onChange, placeholder = 'Tell your story…' }) {
  const [uploading, setUploading] = useState(false)

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
        link: { openOnClick: false, autolink: true, HTMLAttributes: { rel: 'noopener noreferrer nofollow' } },
      }),
      Image.configure({ HTMLAttributes: { class: 'rte-image' } }),
      Placeholder.configure({ placeholder }),
    ],
    content,
    editorProps: {
      attributes: { class: 'rte-content' },
      handleDrop(view, event) {
        const file = imageFileFrom(event.dataTransfer?.files)
        if (!file) return false
        event.preventDefault()
        const coords = view.posAtCoords({ left: event.clientX, top: event.clientY })
        setUploading(true)
        uploadContentImage(file)
          .then((url) => {
            const node = view.state.schema.nodes.image.create({ src: url, alt: file.name })
            const pos = coords?.pos ?? view.state.selection.from
            view.dispatch(view.state.tr.insert(pos, node))
          })
          .finally(() => setUploading(false))
        return true
      },
      handlePaste(view, event) {
        const file = imageFileFrom(event.clipboardData?.files)
        if (!file) return false
        event.preventDefault()
        setUploading(true)
        uploadContentImage(file)
          .then((url) => {
            const node = view.state.schema.nodes.image.create({ src: url, alt: file.name })
            view.dispatch(view.state.tr.replaceSelectionWith(node))
          })
          .finally(() => setUploading(false))
        return true
      },
    },
    onUpdate: ({ editor: e }) => onChange(e.getHTML()),
  })

  return (
    <div className="relative">
      <Toolbar editor={editor} />
      <div className="rounded-b-bento-sm border border-line-strong bg-canvas px-4 py-4">
        <EditorContent editor={editor} />
      </div>
      <AnimatePresence>
        {uploading && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            className="absolute right-3 top-3 z-20 flex items-center gap-2 rounded-full bg-ink px-3 py-1.5 text-xs font-medium text-white shadow-md"
          >
            <span className="h-3 w-3 animate-spin rounded-full border-2 border-white/40 border-t-white" />
            Uploading image…
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
