export const SAMPLE_PAPERS = {
  cs: {
    title: "Computer Science - Data Structures",
    institution: "National Institute of Science & Technology",
    department: "Department of Computer Science & Engineering",
    exam: "End Semester Examinations - Autumn 2026",
    subject: "Data Structures and Algorithms",
    code: "CS201",
    semester: "B.Tech Semester 3",
    duration: "3 Hours",
    maxMarks: 100,
    instructions: [
      "Answer all questions in Part A and any five questions in Part B.",
      "All parts of a question must be answered together.",
      "Draw neat diagrams wherever necessary."
    ],
    rawText: `PART A — Answer all questions. Each carries 2 marks.

1. Define Big-O notation and state its significance. (2 marks)
2. Distinguish between linear and non-linear data structures. (2 marks)
3. What is the difference between singly linked list and doubly linked list? (2 marks)
4. State the condition for stack overflow and underflow. (2 marks)
5. Define a circular queue. How does it overcome linear queue limitation? (2 marks)
6. What is a binary search tree (BST)? State its property. (2 marks)
7. Define AVL tree and explain balance factor. (2 marks)
8. Differentiate between BFS and DFS graph traversals. (2 marks)
9. Define hash collision and list two collision resolution techniques. (2 marks)
10. What is the worst-case time complexity of QuickSort? (2 marks)

PART B — Answer any five questions. Each question carries 12 marks.

11. Answer the following:
(a) Explain the algorithm to convert an Infix expression to Postfix using a stack. (6 marks)
(b) Evaluate the postfix expression: 5 3 + 8 2 - * using stack trace. (6 marks)

12. Answer the following:
(a) Write a C or Python function to insert a node at the beginning and end of a Singly Linked List. (6 marks)
(b) Explain the deletion of a node given its key from a Singly Linked List. (6 marks)

13. Describe the operations of insertion and deletion in a Circular Queue with array implementation and boundary condition checks. (12 marks)

14. Construct an AVL tree by inserting the following sequence of keys step by step: 15, 20, 24, 10, 13, 7, 30, 36, 25. Mention the rotation applied at each imbalance. (12 marks)

15. Answer the following:
(a) Explain Dijkstra's algorithm for single-source shortest paths with an example. (8 marks)
(b) Differentiate between Prim's and Kruskal's minimum spanning tree algorithms. (4 marks)

16. Explain Merge Sort algorithm with pseudocode and solve the recurrence relation T(n) = 2T(n/2) + O(n). (12 marks)

17. Describe Open Addressing and Separate Chaining in Hashing with suitable examples and analysis. (12 marks)
`
  },
  math: {
    title: "Engineering Mathematics - Linear Algebra",
    institution: "Metropolitan University",
    department: "Department of Mathematics",
    exam: "Mid-Term Examination 2026",
    subject: "Engineering Mathematics II",
    code: "MAT202",
    semester: "Semester 2",
    duration: "2 Hours",
    maxMarks: 50,
    instructions: [
      "All questions in Part A are compulsory.",
      "Answer any three questions from Part B."
    ],
    rawText: `PART A — Answer all questions.

1. Find the rank of the matrix [[1, 2, 3], [2, 4, 6], [1, 1, 1]]. (2 marks)
2. State Cayley-Hamilton theorem. (2 marks)
3. If lambda is an eigenvalue of A, prove that 1/lambda is an eigenvalue of A^-1. (2 marks)
4. Define orthogonal matrix with an example. (2 marks)
5. Find the divergence of vector field F = x^2 i + y^2 j + z^2 k. (2 marks)

PART B — Answer any three questions.

6. Find the eigenvalues and eigenvectors of the matrix A = [[3, 1, 4], [0, 2, 6], [0, 0, 5]]. (10 marks)
7. Diagonalize the symmetric matrix A = [[1, 2], [2, 1]] by orthogonal transformation. (10 marks)
8. Verify Green's theorem in the plane for integral (xy + y^2)dx + x^2 dy over the closed region bounded by y = x and y = x^2. (10 marks)
9. Solve the system of linear equations using Gauss Elimination: 2x + y + z = 10, 3x + 2y + 3z = 18, x + 4y + 9z = 16. (10 marks)
`
  }
};
