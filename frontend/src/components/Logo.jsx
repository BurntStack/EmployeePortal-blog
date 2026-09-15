import { cn } from '@/utils/cn.js'

/**
 * BurntStack logo mark: the brand's actual artwork (three stacked plates
 * dissolving into a rising flame), served as a cropped, transparent PNG.
 */
export function LogoMark({ className }) {
  return (
    <img
      src="/logo-mark.png"
      alt=""
      className={cn('object-contain', className)}
      width={256}
      height={256}
    />
  )
}
