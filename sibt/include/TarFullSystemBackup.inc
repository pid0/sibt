_excludeAlso =
_destination = /does-not-exist

[Scheduler]
Name = anacron
Interval = 1 day

[Synchronizer]
Name = tar
ExcludedDirs = 
  %(_excludeAlso)s
  /dev 
  '/lost+found' 
  /media 
  /mnt 
  /proc
  /sys
  /run
  /net
  /tmp
  /var/tmp
  /var/cache/pacman
  '/%(_destination)s'

Loc1 = /
Loc2 = %(_destination)s
