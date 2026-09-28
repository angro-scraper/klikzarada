export type UserDashboardPage =
  | 'pregled' | 'zadaci' | 'moji-zadaci' | 'preporuke' | 'dokazi' | 'poruke' | 'obavestenja'
  | 'novcanik' | 'isplate' | 'podaci-isplata' | 'nagrade' | 'misije'
  | 'referral' | 'profil' | 'podrska' | 'zadatak-detalj'

const USER_PAGE_PATHS: Partial<Record<UserDashboardPage, string>> = {
  pregled: '/korisnik/panel',
  zadaci: '/korisnik/zadaci',
  'moji-zadaci': '/korisnik/moji-zadaci',
  preporuke: '/korisnik/preporuke',
  dokazi: '/korisnik/dokazi',
  poruke: '/korisnik/poruke',
  obavestenja: '/korisnik/notifikacije',
  novcanik: '/korisnik/wallet',
  isplate: '/korisnik/isplate',
  'podaci-isplata': '/korisnik/payout-profile-v11',
  nagrade: '/korisnik/motivacija-v115',
  misije: '/korisnik/bedzevi',
  referral: '/korisnik/referral',
  profil: '/korisnik/profil',
  podrska: '/korisnik/tiketi',
}

export function userDashboardPageFromPath(pathname: string): UserDashboardPage {
  if (/^\/korisnik\/zadaci\/\d+$/.test(pathname)) return 'zadatak-detalj'
  const matched = (Object.entries(USER_PAGE_PATHS) as Array<[UserDashboardPage, string]>).find(([, path]) => pathname.startsWith(path))
  return matched?.[0] ?? 'pregled'
}

export function userDashboardPath(page: UserDashboardPage): string | undefined {
  return USER_PAGE_PATHS[page]
}
