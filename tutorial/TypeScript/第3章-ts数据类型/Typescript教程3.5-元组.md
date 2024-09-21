代码运行地址：

在线运行界面 https://www.typescriptlang.org/zh/play

## 5.TypeScript 元组
在 TypeScript 中，元组（Tuple）是一种固定长度且每个元素类型可以不同的数组。以下是 TypeScript 中元组常用的一些内置属性和方法：
### 内置属性：

1. **length:** 
   - 描述：返回元组的长度。
   - 示例：
```typescript
let tuple: [string, number, boolean] = ["Hello", 42, true];
console.log(tuple.length); // 输出 3
```
### 内置方法：

1.  **concat(...items: ConcatArray[]): T[]:** 
   - 描述：连接两个或多个数组或值，并返回一个新数组。
   - 示例：
```typescript
let tuple1: [string, number] = ["Hello", 42];
let tuple2: [boolean] = [true];
let result = tuple1.concat(tuple2);
console.log(result); // 输出 ["Hello", 42, true]
```
 

2.  **join(separator?: string): string:** 
   - 描述：将元组的所有元素连接成一个字符串，可指定分隔符。
   - 示例：
```typescript
let tuple: [string, number, boolean] = ["Hello", 42, true];
let result = tuple.join("-"); // 指定分隔符为 "-"
console.log(result); // 输出 "Hello-42-true"
```
 

3.  **slice(start?: number, end?: number): T[]:** 
   - 描述：提取元组的一个片段，并返回一个新数组。
   - 示例：
```typescript
let tuple: [string, number, boolean] = ["Hello", 42, true];
let slicedTuple = tuple.slice(1, 2);
console.log(slicedTuple); // 输出 [42]
```
 

4.  **toString(): string:** 
   - 描述：将元组转换为字符串。
   - 示例：
```typescript
let tuple: [string, number, boolean] = ["Hello", 42, true];
let result = tuple.toString();
console.log(result); // 输出 "Hello,42,true"
```
 

5.  **indexOf(searchElement: T, fromIndex?: number): number:** 
   - 描述：返回数组中第一次出现指定元素的索引，如果没有找到则返回 -1。
   - 示例：
```typescript
let tuple: [string, number, boolean] = ["Hello", 42, true];
console.log(tuple.indexOf(42)); // 输出 1
```
 

6.  **push(...items: T[]): number:** 
   - 描述：向元组末尾添加一个或多个元素，并返回新的长度。
   - 示例：
```typescript
let tuple: [string, number, boolean] = ["Hello", 42, true];
tuple.push("world");
console.log(tuple); // 输出 ["Hello", 42, true, "world"]
```
 

7.  **pop(): T | undefined:** 
   - 描述：移除元组的最后一个元素并返回该元素。
   - 示例：
```typescript
let tuple: [string, number, boolean] = ["Hello", 42, true];
let lastElement = tuple.pop();
console.log(lastElement); // 输出 true
console.log(tuple); // 输出 ["Hello", 42]
```
