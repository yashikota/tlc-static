----------------------------- MODULE Counter -----------------------------
EXTENDS Integers, Sequences, FiniteSets, TLC, Bags
VARIABLE x
Init == x = 0
Next == x' = (x + 1) % 4
Spec == Init /\ [][Next]_x /\ WF_x(Next)
TypeOK == x \in 0..3
StandardModules == /\ Cardinality({1, 2, 3}) = 3
                   /\ Len(Append(<<1, 2>>, 3)) = 3
                   /\ BagCardinality(SetToBag({1, 2})) = 2
                   /\ ToString(42) = "42"
                   /\ -2 + 3 = 1
                   /\ 5 \div 2 = 2
EventuallyThree == []<>(x = 3)
Bad == x < 3
Impossible == <>(x = 9)
=============================================================================
