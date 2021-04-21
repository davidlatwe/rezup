# rezup

[Rez](https://github.com/nerdvegas/rez) launching environment manager

### Install

```
pip install rezup
```

### Usage

use default container `.main`
```
$ rezup
```

use foo
```
$ rezup use foo
```

use foo and do job
```
$ rezup use foo --do {script.bat}
```

install rez into default container
```
$ rezup use --make {rezup.toml}
```

install rez into container foo
```
$ rezup use foo --make {rezup.toml}
```

remove container foo
```
$ rezup drop foo
```

list containers
```
$ rezup list
```
