import PortalShell from '@/components/PortalShell.jsx'
import { Posts } from '@/pages/AdminWorkspace.jsx'

export default function Review() {
  return <PortalShell title="Pending Review"><Posts pending /></PortalShell>
}
