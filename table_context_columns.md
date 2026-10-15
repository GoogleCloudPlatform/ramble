# Design Document: Auto-generated Columns in Results Tables

## Overview
Results tables in Ramble provide a way to aggregate figures of merit (FOMs) across multiple experiments into a tabular format (e.g., CSV). Previously, columns had to be explicitly defined, which made it difficult to handle applications that produce a variable number of FOMs or FOMs within many dynamically named contexts.

This feature introduces `autocolumns`, which allow results tables to define a template for columns that are generated dynamically based on the contexts found in an experiment's results.

## Motivation
Many HPC applications produce performance data in a structured way where the same metric is reported across different "contexts" (e.g., different message sizes, different iterations, or different components). 

For example, a bandwidth test might report "Bandwidth" for several message sizes:
- Context: `size=64`, FOM: `Bandwidth`
- Context: `size=1024`, FOM: `Bandwidth`

Defining a table with columns for each size would require knowing all sizes in advance and explicitly listing them in the configuration. `autocolumns` allow a single template to discover all such contexts and create corresponding columns.

## Design

### Configuration Schema
The `tables` section of a Ramble configuration now supports an `autocolumns` list alongside the existing `columns` list. Tables also support a `transpose` option.

```yaml
tables:
  - name: my_table
    transpose: true
    autocolumns:
      - name: '{fom_name}'
        figure_of_merit: '(?P<fom_name>.*)'
        context_name: 'bw-*'
        sort_by: ['size']
        where: ['{n_nodes} > 1']
```

#### Fields:
- `name` (required): A template for the column name. It can include variables from the context (e.g., `{size}`), `{fom_name}`, `{context_name}` (the name of the specific context instance), and any named groups from regular expression matching in `context_name` or `figure_of_merit`.
- `context_name` (optional): A glob pattern or regular expression to match the `context_def_name` (the type of context) or the `name` (the specific instance name) of a context. If omitted, it matches the "null" context (FOMs without a context).
- `figure_of_merit` (required): A glob pattern or regular expression to match the name of a FOM within a matched context.
- `figure_of_merit_origin_type` (optional): Filter FOMs by their origin type (e.g., `application`).
- `sort_by` (optional): A list of context variables to sort the generated columns by.
- `where` (optional): A list of predicates that must evaluate to true for the column to be generated for a given experiment.

Tables also support:
- `transpose` (optional): If set to `true`, the table will be transposed before being written out.

### Implementation Details

#### Discovery Phase
When extracting a row for a table (`ResultsTable.extract_row`), Ramble now performs a discovery phase for each `autocolumn` template:
1. Iterate over all `autocolumns` in the table definition.
2. Evaluate any `where` clauses against the current experiment.
3. Iterate over all contexts reported in the application results, including the "null" context if `context_name` is omitted.
4. Match the context's definition name against the template's `context_name` using globbing or regular expressions.
5. If a match is found, iterate over all FOMs in that context.
6. Match the FOM name against the template's `figure_of_merit` using globbing or regular expressions.
7. For each match, generate a unique column name by expanding the `name` template with:
    - Variables from the context.
    - The `{fom_name}`.
    - Any named groups captured by regular expressions in `context_name` or `figure_of_merit`.
8. Create a new `ResultsColumn` object for this specific column if it hasn't been created already.

#### Column Ordering and Sorting
The order of columns in the resulting table is determined by:
1. Explicitly defined `columns`.
2. Generated `autocolumns`.

Within a set of columns generated from the same template, the `sort_by` field determines their relative order. The sorting logic attempts to convert context variables to floats for numeric sorting, falling back to string sorting if conversion fails. This ensures that columns like "BW 64", "BW 256", and "BW 1024" appear in the expected numeric order.

#### Conflicts
If a generated column name conflicts with an explicitly defined column name, the explicitly defined column takes precedence.

## Examples

### Generating columns for different message sizes
```yaml
tables:
  - name: bandwidth_summary
    autocolumns:
      - name: 'Latency {bytes}'
        context_name: 'latency-bytes'
        figure_of_merit: 'Avg'
        sort_by: ['bytes']
```
If the results contain contexts named `latency-bytes` with variables `bytes=64` and `bytes=1024`, this will produce columns "Latency 64" and "Latency 1024".

### Using regular expressions for multiple FOMs and named groups
```yaml
tables:
  - name: all_metrics
    autocolumns:
      - name: '{fom_name} ({size})'
        context_name: 'ctx-(?P<size>.*)'
        figure_of_merit: '(?P<fom_name>.*)'
```
This will match any context starting with `ctx-`, capture the rest of the name into `{size}`, and match any FOM, capturing its name into `{fom_name}`.

### Matching FOMs in the null context
```yaml
tables:
  - name: base_metrics
    autocolumns:
      - name: '{fom_name}'
        figure_of_merit: '*'
```
By omitting `context_name`, this template will match all FOMs that are not within any specific context.

### Extracting all FOMs from all contexts
```yaml
tables:
  - name: all_results
    autocolumns:
      - name: '{context_name} - {fom_name}'
        context_name: '*'
        figure_of_merit: '*'
```
This will generate a column for every single figure of merit in every single context found in the results.

## Related Changes: Success Criteria Globbing
In addition to tables, `success_criteria` of mode `fom_comparison` have been updated to support globbing for both `fom_context` and `fom_name`. This allows a single success criterion to be applied across multiple contexts or multiple FOMs.

```yaml
success_criteria:
  - name: my_check
    mode: fom_comparison
    fom_context: 'bw-*'
    fom_name: 'Bandwidth'
    formula: '{value} > 100'
```
This criterion will pass only if *all* matched FOMs satisfy the formula.
