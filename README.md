# rezup

[Rez](https://github.com/nerdvegas/rez) launching environment manager

### Install

```
pip install rezup
```

### Usage

use default, if container default not exists, get rez from pypi
```
$ rezup
```

use foo
```
$ rezup use foo
```

use foo and do job
```
$ rezup use foo --do job
```

install rez into container default
```
$ rezup add
```

install rez into container foo
```
$ rezup add foo
```

install rez into container live, which will be in edit mode
```
$ rezup add live
```

remove container foo
```
$ rezup drop foo
```

list containers
```
$ rezup list
```
