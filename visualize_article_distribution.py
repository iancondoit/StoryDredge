import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set the style
sns.set_style("whitegrid")
plt.figure(figsize=(10, 6))

# Read the CSV file
df = pd.read_csv('article_distribution.csv')

# Extract percentage values (remove % symbol and convert to float)
df['Percentage'] = df['Percentage'].str.rstrip('%').astype(float)

# Sort by word count range for better visualization
# Create a custom sorting function
def range_sorter(range_str):
    if range_str == '5000+':
        return 6
    lower = int(range_str.split('-')[0])
    return lower

# Apply sorting
df['sort_key'] = df['Word Count Range'].apply(range_sorter)
df = df.sort_values('sort_key').drop('sort_key', axis=1)

# Create the bar chart
plt.figure(figsize=(12, 7))
ax = sns.barplot(x='Word Count Range', y='Percentage', data=df, color='steelblue')

# Add value labels on top of the bars
for i, v in enumerate(df['Percentage']):
    ax.text(i, v + 0.5, f"{v}%", ha='center', fontweight='bold')

# Add article count as text inside or at the base of each bar
for i, (_, row) in enumerate(df.iterrows()):
    ax.text(i, row['Percentage']/2, f"{row['Articles']} articles", 
            ha='center', va='center', color='white', fontweight='bold')

# Customize the plot
plt.title('Distribution of Newspaper Articles by Word Count', fontsize=16, pad=20)
plt.xlabel('Word Count Range', fontsize=14)
plt.ylabel('Percentage of Articles', fontsize=14)
plt.xticks(fontsize=12)
plt.yticks(fontsize=12)
plt.ylim(0, max(df['Percentage']) * 1.1)  # Add some space for the labels

# Save the chart
plt.tight_layout()
plt.savefig('article_distribution.png', dpi=300)
plt.close()

print("Visualization saved as 'article_distribution.png'") 