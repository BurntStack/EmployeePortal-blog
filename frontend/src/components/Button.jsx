import { Link } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'
import { cn } from '@/utils/cn.js'

const MotionLink = motion.create(Link)

const VARIANTS = {
  primary:
    'bg-orange-500 text-white shadow-xs hover:bg-orange-600 active:translate-y-px',
  secondary:
    'bg-white text-ink border border-line-strong hover:border-ink/25 hover:bg-ivory active:translate-y-px',
  ghost: 'text-slate hover:text-ink hover:bg-sand',
  outline: 'text-orange-600 border border-orange-500/35 hover:bg-orange-50 active:translate-y-px',
  link: 'text-orange-600 hover:text-orange-700 underline-offset-4 hover:underline px-0',
}

const SIZES = {
  sm: 'h-9 px-4 text-[0.85rem] gap-1.5 rounded-md',
  md: 'h-11 px-5 text-[0.9rem] gap-2 rounded-lg',
  lg: 'h-12 px-6 text-[0.95rem] gap-2 rounded-lg',
}

/** Polymorphic button. Renders as <Link>, <a> or <button> depending on props. */
export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  to,
  href,
  className,
  ...props
}) {
  const reduceMotion = useReducedMotion()
  const classes = cn(
    'inline-flex items-center justify-center font-semibold tracking-[-0.01em] whitespace-nowrap',
    'transition-colors duration-150 ease-out',
    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-500',
    'disabled:opacity-55 disabled:pointer-events-none',
    SIZES[size],
    VARIANTS[variant],
    className,
  )
  const tap = reduceMotion || props.disabled ? undefined : { scale: 0.96 }
  const hover = reduceMotion || props.disabled ? undefined : { scale: 1.015 }
  const spring = { type: 'spring', stiffness: 500, damping: 30 }

  if (to) {
    return (
      <MotionLink to={to} className={classes} whileTap={tap} whileHover={hover} transition={spring} {...props}>
        {children}
      </MotionLink>
    )
  }
  if (href) {
    return (
      <motion.a href={href} className={classes} whileTap={tap} whileHover={hover} transition={spring} {...props}>
        {children}
      </motion.a>
    )
  }
  return (
    <motion.button className={classes} whileTap={tap} whileHover={hover} transition={spring} {...props}>
      {children}
    </motion.button>
  )
}
