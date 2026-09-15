import { useRef } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { useEditorState } from '@tiptap/react'
import {
  TbBold, TbItalic, TbUnderline, TbStrikethrough,
  TbH1, TbH2, TbH3, TbList, TbListNumbers, TbBlockquote, TbCode,
  TbLink, TbPhoto, TbArrowBackUp, TbArrowForwardUp,
} from 'react-icons/tb'
import { uploadContentImage } from '@/lib/uploadImage.js'
import { cn } from '@/utils/cn.js'

function ToolbarButton({ active, disabled, onClick, label, children }) {
  const reduceMotion = useReducedMotion()
  return (
    <motion.button
      type="button"
      aria-label={label}
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
      whileTap={disabled || reduceMotion ? undefined : { scale: 0.88 }}
      whileHover={disabled || reduceMotion ? undefined : { scale: 1.06 }}
      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
      className={cn(
        'inline-flex h-8 w-8 items-center justify-center rounded-lg text-slate transition-colors',
        'hover:bg-sand hover:text-ink disabled:pointer-events-none disabled:opacity-35',
        active && 'bg-orange-500/12 text-orange-600',
      )}
    >
      {children}
    </motion.button>
  )
}

function Divider() {
  return <span className="mx-1 h-6 w-px shrink-0 bg-line" aria-hidden="true" />
}

/** Sticky formatting toolbar for RichTextEditor — one button group per concern. */
export default function Toolbar({ editor }) {
  const fileInputRef = useRef(null)

  const state = useEditorState({
    editor,
    selector: ({ editor: e }) => ({
      bold: e.isActive('bold'),
      italic: e.isActive('italic'),
      underline: e.isActive('underline'),
      strike: e.isActive('strike'),
      h1: e.isActive('heading', { level: 1 }),
      h2: e.isActive('heading', { level: 2 }),
      h3: e.isActive('heading', { level: 3 }),
      bulletList: e.isActive('bulletList'),
      orderedList: e.isActive('orderedList'),
      blockquote: e.isActive('blockquote'),
      codeBlock: e.isActive('codeBlock'),
      link: e.isActive('link'),
      canUndo: e.can().undo(),
      canRedo: e.can().redo(),
    }),
  })

  if (!editor) return null

  const insertImage = async (file) => {
    if (!file) return
    try {
      const url = await uploadContentImage(file)
      editor.chain().focus().setImage({ src: url, alt: file.name }).run()
    } catch {
      // The editor stays usable even if one image upload fails — the
      // author just doesn't get an inserted image and can retry.
    }
  }

  const setLink = () => {
    const previous = editor.getAttributes('link').href
    const url = window.prompt('Link URL', previous || 'https://')
    if (url === null) return
    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run()
      return
    }
    editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
  }

  return (
    <div className="sticky top-16 z-10 flex flex-wrap items-center gap-0.5 rounded-t-bento-sm border border-b-0 border-line-strong bg-white/95 px-3 py-2 backdrop-blur-sm">
      <ToolbarButton label="Bold" active={state.bold} onClick={() => editor.chain().focus().toggleBold().run()}>
        <TbBold className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Italic" active={state.italic} onClick={() => editor.chain().focus().toggleItalic().run()}>
        <TbItalic className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Underline" active={state.underline} onClick={() => editor.chain().focus().toggleUnderline().run()}>
        <TbUnderline className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Strikethrough" active={state.strike} onClick={() => editor.chain().focus().toggleStrike().run()}>
        <TbStrikethrough className="h-4 w-4" />
      </ToolbarButton>

      <Divider />

      <ToolbarButton label="Heading 1" active={state.h1} onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}>
        <TbH1 className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Heading 2" active={state.h2} onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}>
        <TbH2 className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Heading 3" active={state.h3} onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}>
        <TbH3 className="h-4 w-4" />
      </ToolbarButton>

      <Divider />

      <ToolbarButton label="Bullet list" active={state.bulletList} onClick={() => editor.chain().focus().toggleBulletList().run()}>
        <TbList className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Numbered list" active={state.orderedList} onClick={() => editor.chain().focus().toggleOrderedList().run()}>
        <TbListNumbers className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Quote" active={state.blockquote} onClick={() => editor.chain().focus().toggleBlockquote().run()}>
        <TbBlockquote className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Code block" active={state.codeBlock} onClick={() => editor.chain().focus().toggleCodeBlock().run()}>
        <TbCode className="h-4 w-4" />
      </ToolbarButton>

      <Divider />

      <ToolbarButton label="Link" active={state.link} onClick={setLink}>
        <TbLink className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Insert image" onClick={() => fileInputRef.current?.click()}>
        <TbPhoto className="h-4 w-4" />
      </ToolbarButton>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        hidden
        onChange={(e) => {
          insertImage(e.target.files?.[0])
          e.target.value = ''
        }}
      />

      <Divider />

      <ToolbarButton label="Undo" disabled={!state.canUndo} onClick={() => editor.chain().focus().undo().run()}>
        <TbArrowBackUp className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Redo" disabled={!state.canRedo} onClick={() => editor.chain().focus().redo().run()}>
        <TbArrowForwardUp className="h-4 w-4" />
      </ToolbarButton>
    </div>
  )
}
