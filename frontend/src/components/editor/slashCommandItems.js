import {
  TbH1, TbH2, TbH3, TbList, TbListNumbers, TbBlockquote, TbCode, TbPhoto, TbMinus, TbLetterCase,
} from 'react-icons/tb'
import { uploadContentImage } from '@/lib/uploadImage.js'

function pickImageFile() {
  return new Promise((resolve) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*'
    input.onchange = () => resolve(input.files?.[0] ?? null)
    input.click()
  })
}

/**
 * The "/" command palette (Notion-style block insertion). Each `command`
 * runs after the "/query" text has already been deleted from the doc, with
 * the cursor left exactly where that text was.
 */
export const SLASH_COMMAND_ITEMS = [
  {
    title: 'Text',
    icon: TbLetterCase,
    keywords: ['paragraph', 'text'],
    command: ({ editor, range }) => editor.chain().focus().deleteRange(range).setParagraph().run(),
  },
  {
    title: 'Heading 1',
    icon: TbH1,
    keywords: ['h1', 'heading', 'title'],
    command: ({ editor, range }) => editor.chain().focus().deleteRange(range).setNode('heading', { level: 1 }).run(),
  },
  {
    title: 'Heading 2',
    icon: TbH2,
    keywords: ['h2', 'heading', 'subtitle'],
    command: ({ editor, range }) => editor.chain().focus().deleteRange(range).setNode('heading', { level: 2 }).run(),
  },
  {
    title: 'Heading 3',
    icon: TbH3,
    keywords: ['h3', 'heading'],
    command: ({ editor, range }) => editor.chain().focus().deleteRange(range).setNode('heading', { level: 3 }).run(),
  },
  {
    title: 'Bullet List',
    icon: TbList,
    keywords: ['bullet', 'list', 'ul'],
    command: ({ editor, range }) => editor.chain().focus().deleteRange(range).toggleBulletList().run(),
  },
  {
    title: 'Numbered List',
    icon: TbListNumbers,
    keywords: ['numbered', 'ordered', 'list', 'ol'],
    command: ({ editor, range }) => editor.chain().focus().deleteRange(range).toggleOrderedList().run(),
  },
  {
    title: 'Quote',
    icon: TbBlockquote,
    keywords: ['quote', 'blockquote', 'citation'],
    command: ({ editor, range }) => editor.chain().focus().deleteRange(range).toggleBlockquote().run(),
  },
  {
    title: 'Code Block',
    icon: TbCode,
    keywords: ['code', 'snippet', 'pre'],
    command: ({ editor, range }) => editor.chain().focus().deleteRange(range).toggleCodeBlock().run(),
  },
  {
    title: 'Divider',
    icon: TbMinus,
    keywords: ['divider', 'hr', 'separator', 'line'],
    command: ({ editor, range }) => editor.chain().focus().deleteRange(range).setHorizontalRule().run(),
  },
  {
    title: 'Image',
    icon: TbPhoto,
    keywords: ['image', 'picture', 'photo', 'upload'],
    command: async ({ editor, range }) => {
      editor.chain().focus().deleteRange(range).run()
      const file = await pickImageFile()
      if (!file) return
      const url = await uploadContentImage(file)
      editor.chain().focus().setImage({ src: url, alt: file.name }).run()
    },
  },
]

export function filterSlashCommands(query) {
  const q = query.toLowerCase().trim()
  if (!q) return SLASH_COMMAND_ITEMS
  return SLASH_COMMAND_ITEMS.filter(
    (item) => item.title.toLowerCase().includes(q) || item.keywords.some((k) => k.includes(q)),
  )
}
