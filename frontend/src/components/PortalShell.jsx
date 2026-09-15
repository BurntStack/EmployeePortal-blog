import { Link, NavLink } from 'react-router-dom'
import { FiLogOut } from 'react-icons/fi'
import { useAuth } from '@/context/AuthContext.jsx'
import { cn } from '@/utils/cn.js'

const LINKS = [
  { to: '/', label: 'My Posts', end: true },
  { to: '/posts/new', label: 'New Post', end: true },
]

/** Shell for every authenticated portal screen: no public Navbar/Footer. */
export default function PortalShell({ title, children }) {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-ivory">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-6 px-5 sm:px-8">
          <Link to="/" className="font-display text-lg font-bold tracking-[-0.02em] text-ink">
            Burnt<span className="text-orange-600">Stack</span> <span className="text-mute font-medium">Portal</span>
          </Link>
          <nav className="hidden items-center gap-6 sm:flex" aria-label="Portal">
            {LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                className={({ isActive }) =>
                  cn('text-sm font-medium transition-colors', isActive ? 'text-orange-600' : 'text-slate hover:text-ink')
                }
              >
                {link.label}
              </NavLink>
            ))}
            {user?.is_staff && (
              <NavLink
                to="/review"
                className={({ isActive }) =>
                  cn('text-sm font-medium transition-colors', isActive ? 'text-orange-600' : 'text-slate hover:text-ink')
                }
              >
                Review
              </NavLink>
            )}
          </nav>
          <div className="flex items-center gap-4">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-semibold text-ink">{user?.first_name} {user?.last_name}</p>
              <p className="text-xs text-mute">{user?.is_staff ? 'Admin' : 'Employee'}</p>
            </div>
            <button
              type="button"
              onClick={logout}
              aria-label="Log out"
              className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-line-strong text-slate transition-colors hover:border-orange-400/60 hover:text-orange-600"
            >
              <FiLogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-10 sm:px-8">
        {title && <h1 className="font-display text-2xl font-bold text-ink">{title}</h1>}
        <div className={title ? 'mt-8' : ''}>{children}</div>
      </main>
    </div>
  )
}
