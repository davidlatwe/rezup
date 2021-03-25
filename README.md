# rezup

Rez launching environment manager

### Usage

use default, if container default not exists, get rez from pypi
```
$ rezup
```

use foo
```
$ rezup --use foo
```

use foo and do job
```
$ rezup --use foo --do job
```

use default to do job
```
$ rezup --do job
```

install rez into container default
```
$ rezup add
```

install rez into container foo
```
$ rezup add --name foo
```

install rez into container live, which will be in edit mode
```
$ rezup add --name live
```

remove container foo
```
$ rezup drop --name foo
```

list containers
```
$ rezup list
```
