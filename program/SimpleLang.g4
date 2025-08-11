grammar SimpleLang;

prog: stat+ ;

	stat: expr NEWLINE ;

expr: expr op=('*'|'/') expr       # MulDiv
    | expr op=('+'|'-') expr       # AddSub
    | expr op=POW expr          # Power
    | expr op=MOD expr           # Modulus
    | INT                          # Int
    | FLOAT                        # Float
    | STRING                       # String
    | BOOL                         # Bool
    | '(' expr ')'                 # Parens
    ;

INT: [0-9]+ ;
FLOAT: [0-9]+'.'[0-9]* ;
POW: '**';
MOD: '%';
STRING: '"' .*? '"' ;
BOOL: 'true' | 'false' ;
NEWLINE: '\r'? '\n' ;
WS: [ \t]+ -> skip ;
